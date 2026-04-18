# Journal

## 2026-04-18 - Thinking-model support

Several FiNER smoke runs started failing in a strange way: the API call returned a
valid-looking chat completion object, but `message.content` was `None`, so ACE logged
`API returned None content` and marked the sample incorrect. The failures were much
more common on thinking models such as `openai/gpt-oss-20b` and
`minimax/minimax-m2.7` through OpenRouter than on `openai/gpt-oss-120b`.
Curator calls also occasionally crashed while the OpenAI client was parsing malformed
provider JSON.

The important distinction is that the original ACE paper used DeepSeek-V3.1 in
non-thinking mode. That path expects the model's visible answer to arrive directly in
`message.content`. Our current OpenRouter runs use thinking models. Those models can
spend the completion budget on hidden or provider-exposed reasoning first, and if the
overall completion cap is too small, the provider may return reasoning without a
visible answer. That looks like an empty response to the original ACE integration even
though the model did produce tokens.

We kept the ACE prompts neutral and did not add thinking-model-specific prompt
instructions. Instead, the integration now gives thinking models a separate default
reasoning budget of 4096 tokens and a larger default overall completion budget of
8192 tokens. The visible answer remains the only text consumed by ACE's Generator,
Reflector, and Curator logic, while any provider-returned reasoning is recorded
separately in detailed call logs.

The MAESTRO/OpenTelemetry spans now track the same split: visible output size,
reasoning size, finish reason, total token usage, and reasoning token usage when the
provider reports it. This keeps non-thinking and thinking runs comparable at the ACE
algorithm level while making the transport behavior observable enough to diagnose
provider failures, budget exhaustion, and malformed API responses.
