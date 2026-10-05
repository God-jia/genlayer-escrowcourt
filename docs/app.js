import { createClient } from 'https://esm.sh/genlayer-js@1.1.8';
import {
  localnet,
  studionet,
  testnetAsimov,
  testnetBradbury,
} from 'https://esm.sh/genlayer-js@1.1.8/chains';

const NETWORKS = { localnet, studionet, testnetAsimov, testnetBradbury };
const STORE = { address: 'escrowcourt.contract', network: 'escrowcourt.network' };

const DEFAULT_MILESTONES = [
  {
    id: 'M1',
    title: 'Landing page',
    criteria: [
      'A responsive landing page renders correctly on a mobile viewport.',
      'The hero section states the product name and the primary call to action.',
    ],
    share_bps: 6000,
  },
  {
    id: 'M2',
    title: 'API integration',
    criteria: ['The contact form posts to a working endpoint and stores the submission.'],
    share_bps: 4000,
  },
];

const el = (tag, className, text) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = String(text);
  return node;
};

const $ = (id) => document.getElementById(id);

let networkKey = localStorage.getItem(STORE.network) || 'studionet';
let contractAddress = localStorage.getItem(STORE.address) || '';
let account = null;
let client = createClient({ chain: NETWORKS[networkKey] });

// ------------------------------------------------------------------ reporting

function log(message, kind) {
  const node = $('log');
  node.hidden = false;
  node.className = 'log' + (kind ? ' ' + kind : '');
  node.textContent = message;
}

function report(node, text, kind) {
  if (node) {
    node.textContent = text;
    node.className = 'out' + (kind ? ' ' + kind : '');
  } else {
    log(text, kind);
  }
}

function errorText(error) {
  if (!error) return 'Unknown error';
  return error.shortMessage || error.message || String(error);
}

function fail(node, error) {
  const message = errorText(error);
  report(node, message, 'error');
  if (node) log(message, 'error');
}

// --------------------------------------------------------------------- render

function kv(rows) {
  const list = el('dl', 'kv');
  for (const [key, value] of rows) {
    list.append(el('dt', null, key));
    list.append(el('dd', null, value === undefined || value === null ? '\u2014' : value));
  }
  return list;
}

function badge(status) {
  return el('span', 'badge ' + status, status);
}

function renderRuling(container, ruling) {
  const rows = el('div', 'criteria');
  for (const item of ruling.criteria || []) {
    const row = el('div', 'criterion');
    row.append(el('span', 'cidx', '#' + item.index));
    row.append(el('span', 'v-' + item.verdict, item.verdict));
    row.append(el('span', null, item.reason));
    rows.append(row);
  }
  container.append(rows);
  container.append(
    kv([
      ['Settlement', ruling.result],
      ['Freelancer receives', ruling.freelancer_cut],
      ['Client receives', ruling.client_cut],
      ['Deliverable reachable', ruling.deliverable_available ? 'yes' : 'no'],
      ['Confidence', ruling.confidence],
      ['Reasoning', ruling.reasoning],
    ]),
  );
}

function renderJob(container, record) {
  container.replaceChildren();
  container.append(badge(record.status));
  container.append(
    kv([
      ['Job id', record.id],
      ['Title', record.title],
      ['Client', record.client],
      ['Freelancer', record.freelancer || '(not accepted yet)'],
      ['Escrow amount', record.amount],
      ['Deliverable location', record.deliverable_url],
    ]),
  );
  container.append(el('h3', null, 'Brief'));
  container.append(el('p', 'body', record.brief));

  container.append(el('h3', null, 'Milestones'));
  for (const milestone of record.milestones) {
    const card = el('div', 'milestone');
    const head = el('div', 'ms-head');
    head.append(el('span', 'rid', milestone.id));
    head.append(el('span', 'ms-title', milestone.title));
    head.append(el('span', 'ms-share', (milestone.share_bps / 100).toFixed(2) + '%'));
    head.append(badge(milestone.status));
    card.append(head);

    const list = el('ul', 'criteria-list');
    for (const criterion of milestone.criteria) {
      list.append(el('li', null, criterion));
    }
    card.append(list);

    if (milestone.evidence_url) {
      card.append(
        kv([
          ['Evidence', milestone.evidence_url],
          ['Submission note', milestone.submission_note],
        ]),
      );
    }
    if (milestone.dispute_claim) {
      card.append(kv([['Dispute claim', milestone.dispute_claim]]));
    }
    if (milestone.ruling) {
      card.append(el('h4', null, 'Ruling (' + milestone.ruling.source + ')'));
      if (milestone.ruling.source === 'adjudication') {
        renderRuling(card, milestone.ruling);
      } else {
        card.append(kv([['Settlement', milestone.ruling.result], ['Reasoning', milestone.ruling.reasoning]]));
      }
    }
    container.append(card);
  }
}

function renderTrack(container, address, reputation, balance) {
  container.replaceChildren();
  container.append(el('h3', null, 'Track record'));
  container.append(
    kv([
      ['Address', address],
      ['Ledger balance', balance],
      ['Milestones released', reputation.released],
      ['Milestones refunded', reputation.refunded],
      ['Milestones split', reputation.split],
      ['Disputes raised', reputation.disputes_raised],
    ]),
  );
}

function renderLedger(container, ledger) {
  container.replaceChildren();
  container.append(el('h3', null, 'Settlement ledger'));
  const entries = Object.entries(ledger);
  if (!entries.length) {
    container.append(el('p', 'hint', 'No settlements recorded yet.'));
    return;
  }
  const list = el('dl', 'kv');
  for (const [address, amount] of entries) {
    list.append(el('dt', null, address));
    list.append(el('dd', null, amount));
  }
  container.append(list);
}

// ------------------------------------------------------------------ chain i/o

function requireContract(node) {
  if (!contractAddress) {
    report(node, 'Set the EscrowCourt contract address first.', 'error');
    return false;
  }
  return true;
}

async function read(functionName, args = []) {
  return client.readContract({ address: contractAddress, functionName, args });
}

async function send(functionName, args, node, ok) {
  if (!account) {
    report(node, 'Connect a wallet first.', 'error');
    return null;
  }
  if (!requireContract(node)) return null;

  try {
    report(node, 'Sending transaction\u2026');
    const hash = await client.writeContract({
      address: contractAddress,
      functionName,
      args,
      value: 0n,
    });

    report(node, 'Submitted ' + hash + '\nWaiting for finalization\u2026');
    const tx = await client.waitForTransactionReceipt({
      hash,
      status: 'FINALIZED',
      interval: 4000,
      retries: 150,
    });

    if (tx.txExecutionResultName !== 'FINISHED_WITH_RETURN') {
      throw new Error(
        'Transaction ' + tx.statusName + ' / ' + (tx.txExecutionResultName || 'no execution result'),
      );
    }

    report(node, typeof ok === 'function' ? ok(tx) : ok, 'ok');
    log('Confirmed ' + hash);
    return tx;
  } catch (error) {
    fail(node, error);
    return null;
  }
}

const toU256 = (value) => {
  const trimmed = String(value).trim();
  return BigInt(trimmed === '' ? '0' : trimmed);
};

// ---------------------------------------------------------------- interaction

function switchTab(name) {
  for (const tab of document.querySelectorAll('.tab')) {
    tab.classList.toggle('active', tab.dataset.tab === name);
  }
  for (const panel of document.querySelectorAll('.panel')) {
    panel.hidden = panel.id !== 'panel-' + name;
  }
}

function setWalletState() {
  const node = $('walletState');
  node.textContent = account
    ? 'wallet: ' + account.slice(0, 6) + '\u2026' + account.slice(-4)
    : 'wallet: not connected';
  node.classList.toggle('on', Boolean(account));
}

function setContractState() {
  const node = $('contractState');
  node.textContent = contractAddress
    ? contractAddress.slice(0, 6) + '\u2026' + contractAddress.slice(-4)
    : 'not set';
  node.classList.toggle('on', Boolean(contractAddress));
}

async function connectWallet() {
  try {
    if (!window.ethereum) {
      throw new Error('No browser wallet found (window.ethereum is undefined).');
    }
    const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
    account = accounts[0];
    client = createClient({ chain: NETWORKS[networkKey], account, provider: window.ethereum });
    await client.connect(networkKey);
    setWalletState();
    log('Connected ' + account + ' on ' + networkKey);
  } catch (error) {
    fail(null, error);
  }
}

function applyNetwork(key) {
  networkKey = key;
  localStorage.setItem(STORE.network, key);
  client = account
    ? createClient({ chain: NETWORKS[key], account, provider: window.ethereum })
    : createClient({ chain: NETWORKS[key] });
  if (account) {
    client.connect(key).catch((error) => fail(null, error));
  }
  log('Network: ' + key);
}

async function refreshTotals() {
  try {
    const total = await read('total_jobs');
    $('jId').value = Number(total) > 0 ? String(Number(total) - 1) : '0';
    $('aId').value = Number(total) > 0 ? String(Number(total) - 1) : '0';
    return Number(total);
  } catch (error) {
    return null;
  }
}

async function loadJobInto(container, id) {
  const raw = await read('get_job', [toU256(id)]);
  const record = JSON.parse(raw);
  renderJob(container, record);
  return record;
}

// ----------------------------------------------------------------------- init

function init() {
  const select = $('network');
  for (const key of Object.keys(NETWORKS)) {
    const option = el('option', null, key);
    option.value = key;
    select.append(option);
  }
  select.value = networkKey;
  select.onchange = () => applyNetwork(select.value);

  $('contract').value = contractAddress;
  setContractState();
  setWalletState();

  $('saveContract').onclick = () => {
    contractAddress = $('contract').value.trim();
    localStorage.setItem(STORE.address, contractAddress);
    setContractState();
    log(contractAddress ? 'Contract address saved.' : 'Contract address cleared.');
    if (contractAddress) refreshTotals();
  };

  $('connect').onclick = connectWallet;

  for (const tab of document.querySelectorAll('.tab')) {
    tab.onclick = () => switchTab(tab.dataset.tab);
  }

  $('pMilestones').value = JSON.stringify(DEFAULT_MILESTONES, null, 2);

  $('createJob').onclick = async () => {
    const tx = await send(
      'create_job',
      [
        $('pTitle').value.trim(),
        $('pBrief').value.trim(),
        $('pDeliverable').value.trim(),
        toU256($('pAmount').value),
        $('pMilestones').value.trim(),
      ],
      $('pOut'),
      'Job created and frozen on-chain.',
    );
    if (!tx) return;
    const total = await refreshTotals();
    if (total !== null) {
      report($('pOut'), 'Job #' + (total - 1) + ' created. A freelancer can now accept it.', 'ok');
    }
  };

  $('loadJob').onclick = async () => {
    try {
      await loadJobInto($('jView'), $('jId').value);
    } catch (error) {
      fail($('jOut'), error);
    }
  };

  $('acceptJob').onclick = async () => {
    const id = toU256($('jId').value);
    const tx = await send('accept_job', [id], $('jOut'), 'Job accepted. You are the freelancer.');
    if (tx) {
      try {
        await loadJobInto($('jView'), id);
      } catch (error) {
        fail(null, error);
      }
    }
  };

  $('submitMilestone').onclick = async () => {
    const id = toU256($('jId').value);
    const tx = await send(
      'submit_milestone',
      [id, $('jMilestone').value.trim(), $('jEvidence').value.trim(), $('jNote').value.trim()],
      $('jOut'),
      'Milestone submitted. The client can approve or dispute it.',
    );
    if (tx) {
      try {
        await loadJobInto($('jView'), id);
      } catch (error) {
        fail(null, error);
      }
    }
  };

  $('approveMilestone').onclick = async () => {
    const id = toU256($('jId').value);
    const tx = await send(
      'approve_milestone',
      [id, $('jMilestone').value.trim()],
      $('jOut'),
      'Milestone approved and the share released to the freelancer.',
    );
    if (tx) {
      try {
        await loadJobInto($('jView'), id);
      } catch (error) {
        fail(null, error);
      }
    }
  };

  $('disputeMilestone').onclick = async () => {
    const id = toU256($('jId').value);
    const tx = await send(
      'dispute_milestone',
      [id, $('jMilestone').value.trim(), $('jClaim').value.trim()],
      $('jOut'),
      'Milestone disputed. Anyone can now trigger adjudication.',
    );
    if (tx) {
      try {
        await loadJobInto($('jView'), id);
      } catch (error) {
        fail(null, error);
      }
    }
  };

  $('adjudicate').onclick = async () => {
    const id = toU256($('aId').value);
    const tx = await send(
      'adjudicate_milestone',
      [id, $('aMilestone').value.trim()],
      $('aOut'),
      'Adjudication finalized.',
    );
    if (!tx) return;
    try {
      const record = await loadJobInto($('aView'), id);
      const milestone = record.milestones.find((item) => item.id === $('aMilestone').value.trim());
      if (milestone && milestone.ruling) {
        log('Milestone ' + milestone.id + ' settled: ' + milestone.ruling.result);
      }
    } catch (error) {
      fail(null, error);
    }
  };

  $('loadTrack').onclick = async () => {
    if (!requireContract(null)) return;
    const address = $('tAddress').value.trim();
    try {
      const [rawReputation, balance] = await Promise.all([
        read('get_reputation', [address]),
        read('get_balance', [address]),
      ]);
      renderTrack($('tView'), address, JSON.parse(rawReputation), Number(balance));
    } catch (error) {
      fail(null, error);
    }
  };

  $('loadLedger').onclick = async () => {
    if (!requireContract(null)) return;
    try {
      renderLedger($('tView'), JSON.parse(await read('get_ledger')));
    } catch (error) {
      fail(null, error);
    }
  };

  if (contractAddress) refreshTotals();
}

init();
