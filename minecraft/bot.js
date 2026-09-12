const mineflayer = require('mineflayer');
const { Vec3 } = require('vec3');
const { pathfinder, Movements, goals } = require('mineflayer-pathfinder');

class MinecraftLLMAgent {
    constructor(username = 'llm_agent') {
        this.bot = mineflayer.createBot({
            host: 'localhost',
            port: 25565,
            username: username
        });
        
        this.trajectory = [];
        this.currentGoal = "collect 10 wood logs";
        this.woodCount = 0;
        this.targetWoodCount = 10;
        
        this.setupBot();
    }
    
    setupBot() {
        this.bot.loadPlugin(pathfinder);
        
        this.bot.once('spawn', () => {
            console.log('Bot spawned, starting wood collection task');
            const movements = new Movements(this.bot);
            this.bot.pathfinder.setMovements(movements);
            this.startMainLoop();
        });
        
        this.bot.on('error', (err) => console.error('Bot error:', err));
    }
    
    // Get structured state for LLM
    getCurrentState() {
        const inventory = this.bot.inventory.items();
        const woodLogs = inventory.filter(item => 
            item.name.includes('log') || item.name.includes('wood')
        );
        
        this.woodCount = woodLogs.reduce((sum, item) => sum + item.count, 0);
        
        // Find nearby trees with better detection
        const nearbyTrees = this.bot.findBlocks({
            matching: (block) => {
                // Look for all types of log blocks
                return block.name.endsWith('_log') || 
                       block.name.includes('log') ||
                       block.name === 'oak_log' ||
                       block.name === 'birch_log' ||
                       block.name === 'spruce_log' ||
                       block.name === 'jungle_log' ||
                       block.name === 'acacia_log' ||
                       block.name === 'dark_oak_log';
            },
            maxDistance: 64,
            count: 50  // Find more blocks to get better coverage
        });
        
        // Also look for leaves to identify tree areas
        const nearbyLeaves = this.bot.findBlocks({
            matching: (block) => block.name.includes('leaves'),
            maxDistance: 32,
            count: 20
        });
        
        let closestTreeDistance = null;
        if (nearbyTrees.length > 0) {
            const distances = nearbyTrees.map(pos => this.bot.entity.position.distanceTo(pos));
            closestTreeDistance = Math.min(...distances);
        }
        
        return {
            position: this.bot.entity.position,
            inventory: inventory.map(item => ({ name: item.name, count: item.count })),
            woodCount: this.woodCount,
            goal: this.currentGoal,
            nearbyTrees: nearbyTrees.length,
            nearbyLeaves: nearbyLeaves.length,
            closestTreeDistance,
            allTreePositions: nearbyTrees.slice(0, 5), // Include actual positions for debugging
            isComplete: this.woodCount >= this.targetWoodCount
        };
    }
    
    // Execute LLM-generated action
    async executeAction(actionCode) {
        const startTime = Date.now();
        const startState = this.getCurrentState();
        
        try {
            // Create safe execution context
            const safeBot = {
                // Movement actions
                pathfinder: this.bot.pathfinder,
                entity: { position: this.bot.entity.position },
                
                // Safe mining function
                mineBlock: async (blockPos) => {
                    const block = this.bot.blockAt(blockPos);
                    if (block && block.name.includes('log')) {
                        await this.bot.dig(block);
                        return { success: true, block: block.name };
                    }
                    return { success: false, reason: 'Invalid block' };
                },
                
                // Safe movement function
                moveTo: async (position) => {
                    await this.bot.pathfinder.goto(goals.GoalNear(position.x, position.y, position.z, 1));
                    return { success: true };
                },
                
                // Look around to load chunks
                lookAround: async () => {
                    for (let i = 0; i < 4; i++) {
                        await this.bot.look(i * Math.PI / 2, 0); // Look in 4 directions
                        await new Promise(resolve => setTimeout(resolve, 500)); // Wait for chunks to load
                    }
                    return { success: true, action: 'looked_around' };
                },
                
                // Find blocks function
                findBlocks: (options) => this.bot.findBlocks(options),
                
                // Utility functions
                getCurrentState: () => this.getCurrentState()
            };
            
            // Execute the LLM's code with timeout
            const result = await Promise.race([
                this.runCodeWithContext(actionCode, safeBot),
                new Promise((_, reject) => 
                    setTimeout(() => reject(new Error('Action timeout')), 10000)
                )
            ]);
            
            const endState = this.getCurrentState();
            const executionTime = Date.now() - startTime;
            
            // Log trajectory for long-term planner
            this.trajectory.push({
                timestamp: Date.now(),
                startState,
                endState,
                action: actionCode,
                result,
                executionTime,
                success: !result.error
            });
            
            return {
                success: true,
                result,
                stateChange: this.getStateChange(startState, endState),
                executionTime
            };
            
        } catch (error) {
            const endState = this.getCurrentState();
            
            this.trajectory.push({
                timestamp: Date.now(),
                startState,
                endState,
                action: actionCode,
                error: error.message,
                executionTime: Date.now() - startTime,
                success: false
            });
            
            return {
                success: false,
                error: error.message,
                stateChange: this.getStateChange(startState, endState)
            };
        }
    }
    
    // Execute code in controlled context
    async runCodeWithContext(code, context) {
        const func = new Function('bot', 
            'return (async () => {' + code + '})();'
        );
        
        return await func(context);
    }
    
    // Calculate state changes for LLM feedback
    getStateChange(startState, endState) {
        return {
            woodGained: endState.woodCount - startState.woodCount,
            positionChanged: !startState.position.equals(endState.position),
            progressToGoal: endState.woodCount / this.targetWoodCount
        };
    }
    
    // Generate LLM prompt based on current state
    generatePrompt(state, lastResult) {
        let prompt = `You are controlling a Minecraft bot to collect 10 wood logs. Current status:

CURRENT STATE:
- Wood collected: ${state.woodCount}/${this.targetWoodCount}
- Position: ${JSON.stringify(state.position)}
- Nearby trees: ${state.nearbyTrees}
- Goal: ${state.goal}
${state.closestTreeDistance ? `- Closest tree distance: ${state.closestTreeDistance.toFixed(2)}` : ''}

AVAILABLE ACTIONS:
- bot.findBlocks({matching: block => block.name.includes('log'), maxDistance: 32, count: 10})
- bot.moveTo(position) 
- bot.mineBlock(position)
- bot.getCurrentState()

`;

        if (lastResult) {
            prompt += `LAST ACTION RESULT: ${JSON.stringify(lastResult, null, 2)}\n\n`;
        }
        
        if (state.isComplete) {
            prompt += `TASK COMPLETE! You have collected ${state.woodCount} wood logs.\n`;
            return prompt;
        }
        
        prompt += `Generate JavaScript code to take the next action towards collecting wood logs. Focus on efficiency.

RESPONSE FORMAT:
\`\`\`javascript
// Your code here
\`\`\``;
        
        return prompt;
    }
    
    // Main execution loop
    async startMainLoop() {
        let stepCount = 0;
        let lastResult = null;
        
        while (this.woodCount < this.targetWoodCount && stepCount < 50) {
            const currentState = this.getCurrentState();
            
            if (currentState.isComplete) {
                console.log(`Task completed! Collected ${this.woodCount} wood logs in ${stepCount} steps.`);
                break;
            }
            
            // Generate LLM prompt
            const prompt = this.generatePrompt(currentState, lastResult);
            console.log(`\n--- Step ${stepCount + 1} ---`);
            console.log(`Wood: ${this.woodCount}/${this.targetWoodCount}`);
            
            // Debug current state
            console.log(`Position: (${currentState.position.x.toFixed(1)}, ${currentState.position.y.toFixed(1)}, ${currentState.position.z.toFixed(1)})`);
            console.log(`Nearby trees: ${currentState.nearbyTrees}`);
            console.log(`Closest tree distance: ${currentState.closestTreeDistance?.toFixed(2) || 'N/A'}`);
            
            // TODO: Replace with actual LLM API call
            const llmResponse = await this.mockLLMResponse(currentState);
            console.log('Generated action:', llmResponse.substring(0, 100) + '...');
            
            // Execute the action
            const result = await this.executeAction(llmResponse);
            lastResult = result;
            
            console.log(`Action result:`, result.success ? 'SUCCESS' : 'FAILED');
            console.log(`Action response:`, result.result);
            if (result.stateChange.woodGained > 0) {
                console.log(`Wood gained: +${result.stateChange.woodGained}`);
            }
            
            stepCount++;
            await new Promise(resolve => setTimeout(resolve, 1000)); // Brief pause
        }
        
        console.log('\n=== TRAJECTORY SUMMARY ===');
        console.log(`Total steps: ${stepCount}`);
        console.log(`Wood collected: ${this.woodCount}`);
        console.log(`Success rate: ${this.trajectory.filter(t => t.success).length}/${this.trajectory.length}`);
        
        // This trajectory data would feed into your long-term planner
        return this.trajectory;
    }
    
    // Mock LLM response for testing - replace with actual LLM API
    async mockLLMResponse(state) {
        return `
    // Look around first to load chunks
    await bot.lookAround();

    let mined = 0;
    const needed = 10;

    while (mined < needed) {
        // Find the nearest log block
        const trees = bot.findBlocks({
            matching: block => block?.name?.includes?.('log') || block?.name?.includes?.('wood'),
            maxDistance: 64,
            count: 1
        });

        if (!trees || trees.length === 0) {
            console.log(\`No logs found, trying to explore\`);
            const pos = bot.entity.position;
            const randomPos = {
                x: pos.x + (Math.random() - 0.5) * 60,
                y: pos.y,
                z: pos.z + (Math.random() - 0.5) * 60
            };
            await bot.moveTo(randomPos);
            continue;
        }

        const treePos = trees[0];
        console.log(\`[Step \${mined + 1}] Moving to tree at:\`, treePos);
        await bot.moveTo(treePos);

        try {
            const result = await bot.mineBlock(treePos);
            console.log(\`[Step \${mined + 1}] Mined log at \${JSON.stringify(treePos)}\`);
            mined += 1;
        } catch (err) {
            console.log(\`[Step \${mined + 1}] Failed to mine log at \${JSON.stringify(treePos)}:\`, err.message);
        }
    }

    return { action: 'mined_logs', count: mined };
`;
    }
}

// Usage
const agent = new MinecraftLLMAgent();

module.exports = MinecraftLLMAgent;