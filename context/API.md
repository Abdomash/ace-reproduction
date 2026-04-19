# Local API Usage

Ollama API (which also supports OpenAI API)

curl -s http://10.68.186.140:11434/api/tags | jq '.models[].name'

"qwen3-coder:latest"
"gpt-oss:20b"
"qwen3:32b"
"qwq:32b"
"qwq:latest"
"yi:34b"
"nous-hermes2:latest"
"command-r-plus:latest"
"llama3:latest"
"phi3:latest"
"mistral:latest"
"mistral:instruct"
"openchat:latest"
"llama2:latest"

curl -s http://10.68.186.140:11434/api/generate -d '{ "model": "gpt-oss:20b", "prompt": "How are you today?", "stream": false}' | jq '.response'

"I’m just a stream of code, so I don’t have feelings—but I’m here and ready to help! How about you—how’s your day going?"

# Minimax API

Use Openrouter api key and endpoint. For smoke runs, just use GPT-oss:20b locally, and switch to Openrouter api key when ready for full runs.


