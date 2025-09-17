document.addEventListener('DOMContentLoaded', () => {
    const nodeList = document.getElementById('node-list');
    const nodeStatus = document.getElementById('node-status');
    const runStressTestButton = document.getElementById('run-stress-test');
    const testMessage = document.getElementById('test-message');
    const testOutput = document.getElementById('test-output');

    async function fetchRayNodes() {
        try {
            const response = await fetch('/api/ray_nodes');
            const data = await response.json();

            if (response.ok) {
                nodeList.innerHTML = '';
                if (data.length > 0) {
                    data.forEach(node => {
                        const listItem = document.createElement('li');
                        listItem.textContent = `Node ID: ${node.NodeID}, Address: ${node.NodeManagerAddress}, State: ${node.State}, Resources: ${JSON.stringify(node.Resources)}`;
                        nodeList.appendChild(listItem);
                    });
                    nodeStatus.textContent = `Found ${data.length} Ray nodes.`;
                } else {
                    nodeStatus.textContent = 'No Ray nodes found.';
                }
            } else {
                nodeStatus.textContent = `Error: ${data.error || 'Failed to fetch Ray nodes'}`;
            }
        } catch (error) {
            nodeStatus.textContent = `Error fetching Ray nodes: ${error.message}`;
            console.error('Error fetching Ray nodes:', error);
        }
    }

    async function runStressTest() {
        runStressTestButton.disabled = true;
        testMessage.textContent = 'Starting stress test... This may take a while.';
        testOutput.textContent = '';

        try {
            const response = await fetch('/api/run_stress_test', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            const data = await response.json();

            if (response.ok) {
                testMessage.textContent = `Stress test initiated! Task ID: ${data.task_id}. Check server logs for full output.`;
                // You might want to implement polling here to fetch the task status/output
                // For now, we'll just display the initial message.
            } else {
                testMessage.textContent = `Error starting stress test: ${data.error || 'Unknown error'}`;
            }
            if (data.stdout) {
                testOutput.textContent += `STDOUT:\n${data.stdout}\n`;
            }
            if (data.stderr) {
                testOutput.textContent += `STDERR:\n${data.stderr}\n`;
            }

        } catch (error) {
            testMessage.textContent = `Error running stress test: ${error.message}`;
            console.error('Error running stress test:', error);
        } finally {
            runStressTestButton.disabled = false;
        }
    }

    runStressTestButton.addEventListener('click', runStressTest);

    // Fetch nodes on page load and periodically
    fetchRayNodes();
    setInterval(fetchRayNodes, 5000); // Refresh every 5 seconds
});