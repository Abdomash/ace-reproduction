# Journal

## 2026-04-19 - OpenRouter FiNER smoke comparison

Finished the 2026-04-19 FiNER smoke experiments comparing `minimax/minimax-m2.7`,
`openai/gpt-oss-120b:nitro`, and `openai/gpt-oss-20b:nitro` on the same subset
setup.

At the tag-accuracy level, `minimax/minimax-m2.7` showed the strongest improvement:
51.88% initial to 68.44% final, a +16.56pp gain. The two GPT-OSS 120B smoke runs
were also clearly useful, improving from 52.19% to 61.56% (+9.38pp) and from 54.69%
to 66.25% (+11.56pp). By contrast, GPT-OSS 20B only moved from 38.12% to 40.00%
(+1.88pp) and from 40.94% to 41.88% (+0.94pp).

The high-level takeaway is that MiniMax M2.7 had a substantial ACE improvement on
this subset, while GPT-OSS 120B was also pretty good and much stronger than GPT-OSS
20B in these runs.

## 2026-04-18 - Paper-faithful ACE defaults

Several FiNER smoke runs started failing in a strange way: the API call returned a
valid-looking chat completion object, but `message.content` was `None`, so ACE logged
`API returned None content` and marked the sample incorrect. The failures were much
more common on thinking models such as `openai/gpt-oss-20b` and
`minimax/minimax-m2.7` through OpenRouter than on `openai/gpt-oss-120b`.
Curator calls also occasionally crashed while the OpenAI client was parsing malformed
provider JSON.

The important distinction is that the original ACE paper/released-code path uses
standard non-thinking chat-completion behavior. ACE should consume only visible
`message.content` from Generator, Reflector, and Curator calls. Provider-returned
reasoning is diagnostic metadata only and is not passed to the Curator or used to
update the playbook.

The default reproduction path is restored to `max_tokens=4096`, provider JSON mode
off, no OpenRouter reasoning controls, no prompt rewriting, and no hidden/provider
reasoning inputs to ACE agents. The unified experiment runner no longer exposes
thinking/reasoning flags or a JSON-mode preset.

The retained robustness layer is deliberately narrow: empty visible content and
malformed provider JSON are logged as provider-call failures, counted as failed
calls/samples where the workflow can continue, and are not retried. Timeout,
rate-limit, and server-error retry behavior remains operational transport handling.
