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

EscrowCourt moves **real GEN**. Opening a job is `payable`: the escrow is whatever GEN
the client attaches to the `create_job` transaction, and the contract holds it. A
settled share or a refund becomes withdrawable, and the payee pulls it out with
`withdraw`, which emits a real GEN transfer to their account.

---

## Live on studionet

| | |
|---|---|
| Contract | [`0x5b6712CF7ec4509680e9803bAa1640E54D8176B5`](https://explorer-studio.genlayer.com/address/0x5b6712CF7ec4509680e9803bAa1640E54D8176B5) |
| Network | studionet (chain ID 61999) |
| dApp | <https://god-jia.github.io/genlayer-escrowcourt/> |
| Demo video | <https://god-jia.github.io/genlayer-escrowcourt/escrowcourt-demo.mp4> |
| Deploy tx | [`0xeef12d39…0db5a45`](https://explorer-studio.genlayer.com/tx/0xeef12d39a011ea54920315d656ccd500d0e3ba8a4bf072a23b426e40d0db5a45) |
| Escrow amount | `1e15` wei, sent with the `create_job` transaction |

The full lifecycle below was executed against studionet with real validators, real web
fetches and a real LLM round — not a simulation.

| Step | Transaction | Result |
|---|---|---|
| `deploy` | [`0xeef12d39…0db5a45`](https://explorer-studio.genlayer.com/tx/0xeef12d39a011ea54920315d656ccd500d0e3ba8a4bf072a23b426e40d0db5a45) | `EscrowCourt` deployed |
| `create_job` (payable, `1e15` wei) | [`0xa0f6f8ed…ce67667f`](https://explorer-studio.genlayer.com/tx/0xa0f6f8ed1d5b9d8ac0a8afa9c91b128a35b90735e708351ba57c2758ce67667f) | job #0 funded by the contract; milestones `M1` (6000 bps) + `M2` (4000 bps) |
| `accept_job` | [`0x417dfb68…ba7938d1`](https://explorer-studio.genlayer.com/tx/0x417dfb682b191bea45480b23eefe5bdab4ed6fa29643cfad0d3b723fba7938d1) | freelancer assigned |
| `submit_milestone M1` | [`0x9f7d1be2…5dd3541b`](https://explorer-studio.genlayer.com/tx/0x9f7d1be20a8a6f1fce354a1509e7e92ef05a9a97ddb22fb238cc3c6d5dd3541b) | submitted with evidence |
| `dispute_milestone M1` | [`0x17db3085…26e98266`](https://explorer-studio.genlayer.com/tx/0x17db3085a4c47a2bfabc73edf9ec81cb65abedb93a5f2935542f0de326e98266) | client disputes |
| `adjudicate_milestone M1` | [`0x9190e202…9b3362c6`](https://explorer-studio.genlayer.com/tx/0x9190e202bfceb92c0eb2444f61fd5cd08c216bf33631ba2557a4bc799b3362c6) | `split` — freelancer `1e14`, client `5e14` credited |
| `submit_milestone M2` | [`0xaaa29c8b…41a06b99`](https://explorer-studio.genlayer.com/tx/0xaaa29c8bdfd20f51033de0201da39f8a3021387798e33335e4ae269641a06b99) | submitted with evidence |
| `approve_milestone M2` | [`0xbb9751be…0e4b3965`](https://explorer-studio.genlayer.com/tx/0xbb9751be6a07d0b58aeb95a8404d69f8a59bc8f2895c2536bd43bef50e4b3965) | `release` — freelancer `4e14` credited |
| `withdraw` (freelancer) | [`0x7bf45510…ae3234fa`](https://explorer-studio.genlayer.com/tx/0x7bf4551043daffb8e73b299271d2dfdfeee02fa1014f8e3a0b45b3fcae3234fa) | `5e14` wei paid out as a real GEN transfer |
| `withdraw` (client) | [`0x9973f716…577a80`](https://explorer-studio.genlayer.com/tx/0x9973f7164cb23b4283cce6125c2852d0bfb66257326eee1188ec766e71577a80) | `5e14` wei paid out as a real GEN transfer |
| `withdraw` (drained) | [`0xe4661d5f…8929d15`](https://explorer-studio.genlayer.com/tx/0xe4661d5ffbb0c85e7435e1cea9abd1e7e8798bf25122f520d3677c1f48929d15) | called again with nothing left — `SUCCESS`, returns `0` instead of a GenVM error |

### The adjudication record returned on-chain

`M1` carried three criteria. The validators classified them independently and the
contract turned that classification into a settlement:

```json
{
  "result": "split",
  "source": "adjudication",
  "deliverable_available": true,
  "evidence_available": true,
  "confidence": 88,
  "criteria": [
    {
      "index": 0,
      "criterion": "The page is served over HTTPS and returns an HTML document.",
      "verdict": "unclear",
      "reason": "The deliverable HTML was retrieved and appears to be served from a domain that typically uses HTTPS, but the fetch metadata does not explicitly confirm the HTTPS scheme or a 200 OK response."
    },
    {
      "index": 1,
      "criterion": "The page contains a visible top-level heading.",
      "verdict": "unmet",
      "reason": "The delivered page contains no heading element (h1, h2, etc.); it consists only of an SVG icon, several paragraph elements in multiple languages, a link, and a script tag."
    },
    {
      "index": 2,
      "criterion": "The page lists at least three distinct product features.",
      "verdict": "unmet",
      "reason": "The delivered page lists no product features whatsoever; it is a generic IANA example-domain placeholder page with informational text about the domain's purpose."
    }
  ],
  "freelancer_cut": 100000000000000,
  "client_cut": 500000000000000,
  "reasoning": "The deliverable is clearly the default IANA example-domain placeholder page, not a custom-built landing page. It contains no heading and no enumeration of product features, failing criteria 1 and 2 outright. The HTTPS criterion is plausible given the domain but cannot be confirmed from the evidence provided, so it is marked unclear rather than met."
}
```

After settlement the ledger credited `5e14` wei to the freelancer and `5e14` wei to the
client. Both then called `withdraw`, so the ledger and the escrow balance read back as:

```json
{ "0x5e5c124a…9966f3": 0, "0x969c9ea4…462234": 0 }
```

`get_escrow_balance()` returns `0` — every escrowed wei left the contract for a real
account.

```json
{ "released": 1, "refunded": 0, "split": 1, "disputes_raised": 0 }
```

Job #0 ends `completed` with both milestones settled — one by adjudication, one by the
client.

## Demo

A ~35-second walkthrough — posting a job and funding the escrow, reading job #0 back
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
| `create_job(title, brief, deliverable_url, milestones_json)` — `payable` | freezes the brief, the deliverable location and the weighted milestones; shares must total 10 000 bps; the GEN sent with the transaction becomes the escrow, so no amount argument can disagree with it |
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

Value handling: `create_job` is decorated `@gl.public.write.payable` and escrows whatever
`gl.message.value` carries, so a funding call can never revert and strand the client's
GEN. `withdraw` returns `0` instead of reverting when the caller has nothing
withdrawable, so a replay against a drained ledger still succeeds. Payouts leave the
contract with `emit_transfer` to the payee's external account, so the escrow holds and
moves real GEN, not just numbers.

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

# 29 direct-mode unit tests
pytest tests/direct -v
```

The screenshot and video tooling needs a few extra packages:
`pip install pillow numpy opencv-python-headless playwright` (the capture scripts
drive the Chrome already installed on the machine).

The test suite covers the happy path plus every revert: bad milestone JSON, duplicate
ids, shares that do not total 10 000 bps, thin criteria, a create call that sends no
escrow, self-acceptance, double acceptance, cancelling after acceptance, the client
refund on cancellation, submitting out of turn, approving or disputing as the wrong
party, adjudicating without a dispute, double adjudication, withdrawing with nothing to
withdraw (returns 0), unknown ids, and all four settlement paths (`release`, `refund`,
`split`, and `split` when the deliverable is unreachable).

## Deploy it yourself

`tools/deploy_and_demo.py` deploys the contract and runs the entire lifecycle end to
end against studionet, printing every transaction hash: it funds the escrow on
`create_job`, runs a dispute through adjudication, approves the second milestone, then
withdraws both parties' balances as real GEN transfers — and finally calls `withdraw`
once more against the drained ledger to show it returns `0` with a `SUCCESS` result.

```bash
python tools/deploy_and_demo.py
```

It keeps the deployer key in `tools/.deploy_key` (git-ignored) and writes the full
result — address, trace, final job state, escrow balance, ledger and reputation — to
`tools/deployment.json`.

## Layout

```
contracts/escrow_court.py        the Intelligent Contract
tests/direct/test_escrow_court.py 29 direct-mode tests
docs/                            the dApp (GitHub Pages root) + the demo video
tools/deploy_and_demo.py         deploy + full lifecycle (escrow, adjudication, payouts) on studionet
tools/extra_demo.py              fund one more job and release it (leaves a live withdrawable balance)
tools/make_demo.py               compose the demo video from dApp screenshots
tools/shoot.py                   capture the dApp screenshots with headless Chrome
```

## License

MIT — see [LICENSE](LICENSE).
