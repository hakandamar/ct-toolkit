import {
    IExecuteFunctions,
    INodeExecutionData,
    INodeType,
    INodeTypeDescription,
    NodeOperationError,
} from 'n8n-workflow';

export class CtToolkit implements INodeType {
	description: INodeTypeDescription = {
		displayName: 'CT-Toolkit Guardrail',
		name: 'ctToolkit',
		icon: 'file:cttoolkit.svg',
		group: ['transform'],
		version: 1,
		description: 'Prevent identity drift and malicious actions in agentic systems',
		defaults: {
			name: 'CT-Toolkit Guardrail',
		},
		inputs: ['main'],
		outputs: ['main'],
		properties: [
			{
				displayName: 'Server URL',
				name: 'serverUrl',
				type: 'string',
				default: 'http://172.20.10.9:8295',
				description: 'The URL of the CT-Toolkit Guardrail API server (start with ct-toolkit serve)',
				required: true,
			},
			{
				displayName: 'Input Type',
				name: 'inputType',
				type: 'options',
				options: [
					{
						name: 'Pre-Call (Request)',
						value: 'request',
						description: 'Validate user/trigger prompt BEFORE sending to LLM',
					},
					{
						name: 'Post-Call (Response)',
						value: 'response',
						description: 'Validate LLM response AFTER generation',
					},
				],
				default: 'request',
				description: 'Whether to validate the user prompt (pre-call) or the LLM response (post-call)',
				required: true,
			},
			{
				displayName: 'Text to Validate',
				name: 'textToValidate',
				type: 'string',
				default: '={{ $json.texts }}',
				description: 'The prompt or the LLM output to evaluate against the Constitutional Kernel',
				required: true,
			},
			{
				displayName: 'Fail on Block',
				name: 'failOnBlock',
				type: 'boolean',
				default: true,
				description: 'Whether to throw an error and completely stop the workflow if CT-Toolkit blocks the action',
			},
		],
	};

	async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
		const items = this.getInputData();
		const returnData: INodeExecutionData[] = [];

		for (let i = 0; i < items.length; i++) {
			try {
				const serverUrl = this.getNodeParameter('serverUrl', i) as string;
				const inputType = this.getNodeParameter('inputType', i) as string;
				const text = this.getNodeParameter('textToValidate', i) as string;
				const failOnBlock = this.getNodeParameter('failOnBlock', i) as boolean;

				const endpoint = `${serverUrl.replace(/\/$/, '')}/guardrail/check`;

				const body = {
					texts: [text],
					input_type: inputType,
				};

				// Call the CT-Toolkit Guardrail API
				const response = await this.helpers.request({
					method: 'POST',
					url: endpoint,
					body,
					json: true,
				});

				const action = response.action;
				const blockedReason = response.blocked_reason || 'Identity constraint violation.';

				// If blocked and failOnBlock is true, throw workflow error
				if (action === 'BLOCKED') {
					if (failOnBlock) {
						throw new NodeOperationError(this.getNode(), `[CT-Toolkit Intervened] ${blockedReason}`);
					}
					// Otherwise, attach status to pass along the chain gracefully
					items[i].json.ct_toolkit_status = 'BLOCKED';
					items[i].json.ct_toolkit_reason = blockedReason;
				} else {
					items[i].json.ct_toolkit_status = 'PASS';
				}

				returnData.push(items[i]);
			} catch (error) {
				if (this.continueOnFail()) {
					items[i].json = { error: error.message };
					returnData.push(items[i]);
					continue;
				}
				throw error;
			}
		}

		return [returnData];
	}
}
