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
| Contract | [`0x3c065996BF808161c1A52eD7cFc52A6b2401d7A3`](https://explorer-studio.genlayer.com/address/0x3c065996BF808161c1A52eD7cFc52A6b2401d7A3) |
| Network | studionet (chain ID 61999) |
| dApp | <https://god-jia.github.io/genlayer-escrowcourt/> |
| Demo video | <https://god-jia.github.io/genlayer-escrowcourt/escrowcourt-demo.mp4> |
| Deploy tx | [`0xfb8d2ba1…df29a6a`](https://explorer-studio.genlayer.com/tx/0xfb8d2ba1ad46645e0ed3d89ede5369d14649530d02ee7a45c320a7bd4df29a6a) |
| Escrow amount | `1e15` wei, sent with the `create_job` transaction |

The full lifecycle below was executed against studionet with real validators, real web
fetches and a real LLM round — not a simulation.

| Step | Transaction | Result |
|---|---|---|
| `deploy` | [`0xfb8d2ba1…df29a6a`](https://explorer-studio.genlayer.com/tx/0xfb8d2ba1ad46645e0ed3d89ede5369d14649530d02ee7a45c320a7bd4df29a6a) | `EscrowCourt` deployed |
| `create_job` (payable, `1e15` wei) | [`0x577f0ad4…23dda879`](https://explorer-studio.genlayer.com/tx/0x577f0ad4613c99bb62da17a4501ba1010b5fd230deafe3c5626100b423dda879) | job #0 funded by the contract; milestones `M1` (6000 bps) + `M2` (4000 bps) |
| `accept_job` | [`0x8f8fb12b…71affe434`](https://explorer-studio.genlayer.com/tx/0x8f8fb12b00af8d90347306cf9428b7aa56ceb1aba6db1db162668da71affe434) | freelancer assigned |
| `submit_milestone M1` | [`0x738e8164…3521f58e`](https://explorer-studio.genlayer.com/tx/0x738e8164b8abcf76ce98ce47787d304c06142825e19b27ee5cff95143521f58e) | submitted with evidence |
| `dispute_milestone M1` | [`0xdbfed7d2…1d663972`](https://explorer-studio.genlayer.com/tx/0xdbfed7d20b8646c007f7f6bb9c1a7791725faeea2bb6e218a97585bf1d663972) | client disputes |
| `adjudicate_milestone M1` | [`0xe7511a90…ddff36bf7`](https://explorer-studio.genlayer.com/tx/0xe7511a90a8ec42131bebfe9511cbab2d12657ab40d8f3c7d5dbfc30ddff36bf7) | `split` — freelancer `4e14`, client `2e14` credited |
| `submit_milestone M2` | [`0xb6394087…dc124fe5`](https://explorer-studio.genlayer.com/tx/0xb6394087ff3090fa5bc76fc2b45d35d0007ba52bb4aab950a0bb8c88dc124fe5) | submitted with evidence |
| `approve_milestone M2` | [`0x05a0b8b0…dddc005a`](https://explorer-studio.genlayer.com/tx/0x05a0b8b082fd9dc5cb1c1826084f05ef83f83d3fb9f770796da6b1b8dddc005a) | `release` — freelancer `4e14` credited |
| `withdraw` (freelancer) | [`0xe55c75b3…cabb4580`](https://explorer-studio.genlayer.com/tx/0xe55c75b38a6c975625f93e1b8159e5cdbe2288570537727cd8ff92e4cabb4580) | `8e14` wei paid out as a real GEN transfer — the freelancer's wallet balance rises by exactly `8e14` |
| `withdraw` (client) | [`0xb6ede07f…1a8db33c49`](https://explorer-studio.genlayer.com/tx/0xb6ede07fbbd2f54a641c6d85e3a5e185be12fdf028bf718b74769d1a8db33c49) | `2e14` wei paid out as a real GEN transfer |
| `withdraw` (drained) | [`0x2a9a70ad…e4bf4828f5b`](https://explorer-studio.genlayer.com/tx/0x2a9a70ad204773f05fe9b591cfc6f7872f85eb1833c25441c2e46e4bf4828f5b) | called again with nothing left — `SUCCESS`, returns `0` instead of a GenVM error |

### The adjudication record returned on-chain

`M1` carried three criteria. The validators classified them independently and the
contract turned that classification into a settlement:

```json
{
  "result": "split",
  "source": "adjudication",
  "deliverable_available": true,
  "evidence_available": true,
  "confidence": 100,
  "criteria": [
    {
      "index": 0,
      "criterion": "The page returns an HTML document with a body element.",
      "verdict": "met",
      "reason": "The evidence provided contains a complete HTML structure including a body element wrapping the content."
    },
    {
      "index": 1,
      "criterion": "The page contains a visible top-level heading.",
      "verdict": "met",
      "reason": "The page contains a visible <h1> element with the text 'Example Domains'."
    },
    {
      "index": 2,
      "criterion": "The page lists at least three distinct product features.",
      "verdict": "unmet",
      "reason": "The page describes the purpose of example domains but fails to list three distinct product features as required by the brief."
    }
  ],
  "freelancer_cut": 400000000000000,
  "client_cut": 200000000000000,
  "reasoning": "The freelancer provided the source code of the IANA example page as evidence of delivery. While the technical HTML structure and heading requirements are met, the content is purely informational regarding domain usage and lacks the specific 'three distinct product features' mandated in the authoritative job brief."
}
```

After settlement the ledger credited `4e14` wei to the freelancer and `2e14` wei to the
client. Both then called `withdraw`, so the ledger and the escrow balance read back as:

```json
{ "0x5e5c124a…9966f3": 0, "0xd41f5ef7…9679981": 0 }
```

`get_escrow_balance()` returns `0` — every escrowed wei left the contract for a real
account. The freelancer's wallet balance moved from `1e18` before the withdraw to
`1e18 + 8e14` after it, which is the on-chain proof that the payout is a real transfer
and not only a ledger entry.

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
URL can never quietly become a payout. That is why `M1` above settled at `4e14` out of
`6e14`: two `met`, one `unmet`.

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
