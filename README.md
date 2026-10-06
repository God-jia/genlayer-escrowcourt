# EscrowCourt

**Milestone escrow where the acceptance criteria are the judge — built as a GenLayer Intelligent Contract.**

A client opens a job, splits the budget into weighted milestones, and freezes the brief,
the deliverable location and every acceptance criterion on-chain. A freelancer accepts
and submits each milestone with evidence. The client either approves it or disputes it.

A disputed milestone is adjudicated by validators that read the deliverable and the
evidence and classify **every acceptance criterion** as `met` / `unmet` / `unclear`.
The settlement — `release`, `refund`, or `split` — is derived **in code** from those
classifications.

> The model classifies. The contract decides the money.

EscrowCourt moves **real GEN**. Opening a job is `payable`: the client sends exactly the
escrow amount with the transaction and the contract holds it. A settled share or a
refund becomes withdrawable, and the payee pulls it out with `withdraw`, which emits a
real GEN transfer to their account.

---

## Live on studionet

| | |
|---|---|
| Contract | [`0x8A51ca7d8C77859E72DC89d673Ac9A665DcE66F3`](https://explorer-studio.genlayer.com/address/0x8A51ca7d8C77859E72DC89d673Ac9A665DcE66F3) |
| Network | studionet (chain ID 61999) |
| dApp | <https://god-jia.github.io/genlayer-escrowcourt/> |
| Demo video | <https://god-jia.github.io/genlayer-escrowcourt/escrowcourt-demo.mp4> |
| Deploy tx | [`0x04ef35c7…e528bf39`](https://explorer-studio.genlayer.com/tx/0x04ef35c7d93bfd5c3e8da41df412b85cfdb96170f15036cf79083ed1e528bf39) |
| Escrow amount | `1e15` wei, sent with the `create_job` transaction |

The full lifecycle below was executed against studionet with real validators, real web
fetches and a real LLM round — not a simulation.

| Step | Transaction | Result |
|---|---|---|
| `deploy` | [`0x04ef35c7…e528bf39`](https://explorer-studio.genlayer.com/tx/0x04ef35c7d93bfd5c3e8da41df412b85cfdb96170f15036cf79083ed1e528bf39) | `EscrowCourt` deployed |
| `create_job` (payable, `1e15` wei) | [`0x43c18e5f…0531137`](https://explorer-studio.genlayer.com/tx/0x43c18e5fcaae6af2f87db5a84e093ec242e71529a51be4ba5d1d01e830531137) | job #0 funded by the contract; milestones `M1` (6000 bps) + `M2` (4000 bps) |
| `accept_job` | [`0xaaa42d09…dfcb6c25`](https://explorer-studio.genlayer.com/tx/0xaaa42d090b15803ac64e39999d659181ea575657c46731a3ce76dcc5dfcb6c25) | freelancer assigned |
| `submit_milestone M1` | [`0xf4d2b63b…c75c9d6f`](https://explorer-studio.genlayer.com/tx/0xf4d2b63b5e100cb43d6b587ad55209ae693060e7958530f8688422ddc75c9d6f) | submitted with evidence |
| `dispute_milestone M1` | [`0x8489ee59…ebd70c1`](https://explorer-studio.genlayer.com/tx/0x8489ee59c781afb62a26fbc5fa51c1769315a2f2d302ca48c111224e1ebd70c1) | client disputes |
| `adjudicate_milestone M1` | [`0x5f15a59f…f451253b`](https://explorer-studio.genlayer.com/tx/0x5f15a59fa1e2ad3d31dca576515bab7c06b38820d5bdd2f986076846f451253b) | `split` — freelancer `1e14`, client `5e14` credited |
| `submit_milestone M2` | [`0x21f0fe11…4391542d`](https://explorer-studio.genlayer.com/tx/0x21f0fe116488671d65b87bc5465192cae519bc19c9e5d94286b5dbdb4391542d) | submitted with evidence |
| `approve_milestone M2` | [`0xe4976ecc…85fa4436`](https://explorer-studio.genlayer.com/tx/0xe4976ecc6cea95ca4af6e79a205b542f3cc293c743ab3a835e646ad585fa4436) | `release` — freelancer `4e14` credited |
| `withdraw` (freelancer) | [`0x8848c6bb…ef0b4757`](https://explorer-studio.genlayer.com/tx/0x8848c6bb900e339f397cac015603aba0de75863848dcba26fa52e863ef0b4757) | `5e14` wei paid out as a real GEN transfer |
| `withdraw` (client) | [`0xa1463941…f41f62f7`](https://explorer-studio.genlayer.com/tx/0xa1463941bb0697ca711cd4d9b4f4604d8af57fb977e7d65ce2bffad1f41f62f7) | `5e14` wei paid out as a real GEN transfer |

### The adjudication record returned on-chain

`M1` carried three criteria. The validators classified them independently and the
contract turned that classification into a settlement:

```json
{
  "result": "split",
  "source": "adjudication",
  "deliverable_available": true,
  "evidence_available": true,
  "confidence": 92,
  "criteria": [
    {
      "index": 0,
      "criterion": "The page is served over HTTPS and returns an HTML document.",
      "verdict": "unclear",
      "reason": "The retrieved deliverable is HTML content, but there is no reliable evidence here showing the page was served over HTTPS at the agreed URL."
    },
    {
      "index": 1,
      "criterion": "The page contains a visible top-level heading.",
      "verdict": "unmet",
      "reason": "The delivered page snippet contains no visible top-level heading such as an <h1> element."
    },
    {
      "index": 2,
      "criterion": "The page lists at least three distinct product features.",
      "verdict": "unmet",
      "reason": "The page text describes the example domain and warnings about its use, but it does not list at least three distinct product features."
    }
  ],
  "freelancer_cut": 100000000000000,
  "client_cut": 500000000000000,
  "reasoning": "The authoritative judgment should be based on the delivered page content, and that content is available as an HTML snippet. However, the snippet does not demonstrate HTTPS delivery, lacks a visible top-level heading, and does not include a three-feature product list, while the separate evidence appears to be an unrelated IANA reference page rather than the delivered landing page."
}
```

After settlement the ledger credited `5e14` wei to the freelancer and `5e14` wei to the
client. Both then called `withdraw`, so the ledger and the escrow balance read back as:

```json
{ "0x5e5c124a…9966f3": 0, "0xed1fe303…ff99e8": 0 }
```

`get_escrow_balance()` returns `0` — every escrowed wei left the contract for a real
account.

```json
{ "released": 1, "refunded": 0, "split": 1, "disputes_raised": 0 }
```

Job #0 ends `completed` with both milestones settled — one by adjudication, one by the
client.

## Demo

A ~40-second walkthrough — posting a job and funding the escrow, reading job #0 back
from studionet, handing a dispute to the validators, the per-criterion ruling with the
wei-level settlement, and the withdrawable balances — is at
[`docs/escrowcourt-demo.mp4`](docs/escrowcourt-demo.mp4), or streamed from the dApp URL
above. Every frame is the real dApp talking to the deployed contract.

The track-record slide reads a second job (`#1`) that was settled by client approval, so
the freelancer's share is shown sitting in a withdrawable balance before `withdraw`
moves it out of the contract.

## Why this needs GenLayer

An escrow dispute has two halves, and a normal smart contract can only do one of them.

| Half | Nature | Where it belongs |
|---|---|---|
| Does the delivered page actually satisfy criterion 2? | subjective, needs reading a live web page | non-deterministic |
| `release` / `refund` / `split`, the exact split, the counters | mechanical, must be identical for every node | deterministic |

GenLayer lets both halves live in one contract. `gl.nondet.web.render` fetches the
deliverable and the evidence, `gl.nondet.exec_prompt` classifies the criteria, and
`gl.vm.run_nondet_unsafe` runs it under a custom validator that requires every
validator to agree on the **verdicts**, not on the prose.

Everything inside `<deliverable>`, `<evidence>`, `<submission_note>` and `<claim>` is
treated as untrusted data — the prompt explicitly refuses instructions embedded in it,
which matters because the deliverable is attacker-controlled by definition.

## The settlement is derived, never chosen

The prompt is not allowed to pick a number. It only fills in a verdict per criterion.
The contract then computes:

| Verdicts | Resolution | Payout |
|---|---|---|
| every criterion `met` | `release` | freelancer gets the milestone amount |
| every criterion `unmet` | `refund` | freelancer gets nothing |
| anything else (mixed or `unclear`) | `split` | freelancer gets `amount × (2·met + unclear) / (2·n)` |

A missing deliverable forces every affected criterion to `unclear`, so an unreachable
URL can never quietly become a payout. That is why `M1` above settled at `1e14` out of
`6e14`: one `unclear`, two `unmet`.

## Contract API

`contracts/escrow_court.py` — 15 public methods (8 write, 7 view).

| Write | What it does |
|---|---|
| `create_job(title, brief, deliverable_url, amount, milestones_json)` — `payable` | freezes the brief, the deliverable location and the weighted milestones; shares must total 10 000 bps; `gl.message.value` must equal `amount`, so the GEN is escrowed by the contract |
| `accept_job(job_id)` | the freelancer takes the job (the client cannot take their own) |
| `cancel_job(job_id)` | the client cancels while the job is still open; the full escrow becomes withdrawable for the client |
| `submit_milestone(job_id, milestone_id, evidence_url, note)` | freelancer submits a milestone with evidence |
| `approve_milestone(job_id, milestone_id)` | client approves; the milestone share becomes withdrawable for the freelancer |
| `dispute_milestone(job_id, milestone_id, claim)` | client disputes a submitted milestone |
| `adjudicate_milestone(job_id, milestone_id)` | anyone triggers the validator round; the settlement is derived in code and credited to the parties |
| `withdraw()` | the caller pulls their withdrawable balance out as a real GEN transfer |

| View | Returns |
|---|---|
| `get_job(job_id)` | the full job record, including rulings |
| `get_balance(address)` | withdrawable balance of an address |
| `get_withdrawable(address)` | withdrawable balance of an address |
| `get_escrow_balance()` | GEN currently held in escrow by the contract |
| `get_reputation(address)` | `released` / `refunded` / `split` / `disputes_raised` counters |
| `get_ledger()` | the whole withdrawable ledger |
| `total_jobs()` | number of jobs created |

Value handling: `create_job` is decorated `@gl.public.write.payable` and rejects a call
whose `gl.message.value` does not equal the job amount. Payouts leave the contract with
`emit_transfer` to the payee's external account, so the escrow holds and moves real GEN,
not just numbers.

## The dApp

`docs/` is a static site (no build step) that talks to the deployed contract through
`genlayer-js`:

- **Post a job** — write the brief, the deliverable URL and the milestone JSON; the
  app validates that the shares total 10 000 bps before sending.
- **Job workspace** — load a job, accept it, submit milestones, approve or dispute.
- **Adjudicate** — trigger the validator round on a disputed milestone and read back
  the per-criterion ruling.
- **Track record** — per-address reputation and the global ledger.

Set the contract address in the header (it is remembered in `localStorage`), connect a
wallet, and the whole lifecycle can be driven from the browser.

## Run it locally

```bash
python -m venv .venv
.venv/Scripts/activate          # Windows
pip install -r requirements.txt

# static check
genvm-lint check contracts/escrow_court.py

# 28 direct-mode unit tests
pytest tests/direct -v
```

The screenshot and video tooling needs a few extra packages:
`pip install pillow numpy opencv-python-headless playwright` (the capture scripts
drive the Chrome already installed on the machine).

The test suite covers the happy path plus every revert: bad milestone JSON, duplicate
ids, shares that do not total 10 000 bps, thin criteria, a create call whose value does
not match the escrow amount, self-acceptance, double acceptance, cancelling after
acceptance, the client refund on cancellation, submitting out of turn, approving or
disputing as the wrong party, adjudicating without a dispute, double adjudication,
withdrawing with nothing to withdraw, unknown ids, and all four settlement paths
(`release`, `refund`, `split`, and `split` when the deliverable is unreachable).

## Deploy it yourself

`tools/deploy_and_demo.py` deploys the contract and runs the entire lifecycle end to
end against studionet, printing every transaction hash: it funds the escrow on
`create_job`, runs a dispute through adjudication, approves the second milestone, then
withdraws both parties' balances as real GEN transfers.

```bash
python tools/deploy_and_demo.py
```

It keeps the deployer key in `tools/.deploy_key` (git-ignored) and writes the full
result — address, trace, final job state, escrow balance, ledger and reputation — to
`tools/deployment.json`.

## Layout

```
contracts/escrow_court.py        the Intelligent Contract
tests/direct/test_escrow_court.py 28 direct-mode tests
docs/                            the dApp (GitHub Pages root) + the demo video
tools/deploy_and_demo.py         deploy + full lifecycle (escrow, adjudication, payouts) on studionet
tools/extra_demo.py              fund one more job and release it (leaves a live withdrawable balance)
tools/make_demo.py               compose the demo video from dApp screenshots
tools/shoot.py                   capture the dApp screenshots with headless Chrome
```

## License

MIT — see [LICENSE](LICENSE).
