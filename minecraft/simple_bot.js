const mineflayer = require('mineflayer');
const collectBlock = require('mineflayer-collectblock');


//const {spawn} = require('child_process');
const { pathfinder, Movements, goals } = require('mineflayer-pathfinder');
//const { last } = require('lodash');

const getBotState = require('./getBotState');

const axios = require('axios');
const { last } = require('lodash');




const BOT_NAME = 'diamond_bot_15'; // Default bot name
const BOT_TASK = 'mine a diamond'; // Default task

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}





class SimpleLLMAgent {
    constructor(username = BOT_NAME) {
        this.bot = mineflayer.createBot({
            host: 'localhost',
            port: 25565,
            username
        });
        

        this.woodTarget = 20;
        this.woodCount = 0;
        this.trajectory = [];
        this.chatLog = [];

        this.setup();
    }

    setup() {
        this.bot.loadPlugin(pathfinder);
        this.bot.loadPlugin(collectBlock.plugin);

        this.bot.once('spawn', () => {
            const defaultMovements = new Movements(this.bot);
            defaultMovements.digCost = 0.25;
            defaultMovements.liquidCost = 100;
            defaultMovements.dontCreateFlow = true; // Avoid creating water flow

            console.log(this.bot.version, 'version');
            this.bot.pathfinder.setMovements(defaultMovements);
            this.mainLoop();
        });
        this.lastKnownPos = null;

        this.bot.on('move', () => {
            this.lastKnownPos = this.bot.entity.position.clone();
        });

        this.bot.on('death', async () => {
            console.log("[INFO] Bot died!");

            // Wait for the respawn event to ensure the bot is back in the world
            this.bot.once('spawn', async () => {
                await sleep(500); // small buffer to stabilize

                if (this.lastKnownPos) {
                    const { x, y, z } = this.lastKnownPos;
                    const cmd = `/tp ${this.bot.username} ${x.toFixed(2)} ${y.toFixed(2)} ${z.toFixed(2)}`;
                    console.log("[INFO] Teleporting bot back to death location:", cmd);
                    this.bot.chat(cmd);
                } else {
                    console.warn("[WARN] No known position to teleport to!");
                }
            });
        });

        class ChatlogItem {
            constructor(username, message) {
                this.username = username;
                this.message = message;
            }
        }

        this.bot.on('chat', (username, message) => {
            this.chatLog.push(new ChatlogItem(username, message));
            if (this.chatLog.length > 5) {
                this.chatLog.shift(); // Keep only last 5 messages
            }

        console.log(`[${username}] ${message}`);});


        this.bot.on('error', err => console.error('Bot error:', err));
    }

    getWoodCount() {
        return this.bot.inventory.items().filter(item =>
            item.name.includes('log') || item.name.includes('wood')
        ).reduce((sum, item) => sum + item.count, 0);
    }


    async callPythonAgent(state) {
        try {
            const res = await axios.post('http://127.0.0.1:8000/generate-code', state, {
                headers: { 'Content-Type': 'application/json' }
            });
            return { code: res.data.code, response: res.data.response };; // This should be the JS code string
        } catch (err) {
            console.error("[Python Agent Error]", err.message);
            return '';
        }
    }


    async executeLLMAction(codeStr) {
        const fs = require('fs');
        const path = require('path');

        const skillFiles = fs.readdirSync('./basic_skills');
        const skillContext = {};

        for (const file of skillFiles) {
            const skillName = path.basename(file, '.js'); // e.g., "mineBlock"
            skillContext[skillName] = require(`./basic_skills/${file}`);
        }
        const { Vec3 } = require('vec3');

        const safeContext = {
            bot: this.bot,
            mcData: this.mcData,
            Vec3: Vec3,
            ...skillContext
        };

        const additionalBindings = ['Vec3', 'mcData']
        .map(name => `const ${name} = context.${name};`)
        .join('\n');

        const skillBindings = Object.keys(skillContext)
            .map(name => `const ${name} = context.${name};`)
            .join('\n');

        const fn = new Function("context", `
            const bot = context.bot;
            ${skillBindings}
            ${additionalBindings}
            return (async () => {
                ${codeStr}
            })();
        `);

        try {
            return await fn(safeContext);
        } catch (e) {
            console.error("Execution error:", e);
            throw e;
        }
    }

    async mainLoop() {
        let step = 0;

        let lastCode = "";
        let lastResponse = "";
        let lastError = null;
        let lastOutput = null;


        while (step < 100) {
            console.log(`\n[Step ${step}]`);
            const state = getBotState(this.bot, {
                lastCode: lastCode,
                lastResponse: lastResponse,
                lastError: lastError,
                chatLog: this.chatLog, 
                currentTask: BOT_TASK,
                context: '',
                critique: 'Do this efficiently'
            });
            

            //console.log("Bot state:", JSON.stringify(state, null, 2));

            try {
                const response = await this.callPythonAgent(state);

                const code = response.code
                const reasoning = response.response;
                console.log("Generated code:", code);
                lastCode = code;
                lastResponse = reasoning;
                console.log("LLM reasoning:", reasoning);

                const result = await this.executeLLMAction(code);
                lastError = null; // clear the error if successful
                lastOutput = result;
                this.trajectory.push({ step, state, result });
            } catch (error) {
                console.error("Execution error:", error);
                lastError = error.toString(); // or extract just the message
                lastOutput = null;
                this.trajectory.push({ step, state, error: lastError });
            }

            step++;
            await sleep(1000);
        }

        console.log(`\nTask complete: Collected ${this.woodCount} wood logs`);
        console.log(this.trajectory);
    }
}

new SimpleLLMAgent();