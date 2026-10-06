"""Compose the EscrowCourt demo video from dApp screenshots.

Slides are drawn with PIL and encoded with OpenCV (the bundled ffmpeg in this
environment has no PNG decoder, so cv2.VideoWriter is used instead).
"""

import os
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import cv2

SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots")
OUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs",
    "escrowcourt-demo.mp4",
)

W, H = 1280, 720
FPS = 30
HOLD = 5.0
FADE = 0.6

BG = (13, 15, 22)
PANEL = (20, 23, 33)
ACCENT = (124, 92, 255)
GREEN = (74, 222, 128)
TEXT = (232, 234, 242)
MUTED = (150, 156, 176)
BORDER = (38, 42, 58)

FONTS = r"C:\Windows\Fonts"


def font(name, size):
    for candidate in (name, "segoeui.ttf", "arial.ttf"):
        path = os.path.join(FONTS, candidate)
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def base_canvas():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    for y in range(0, H, 4):
        shade = int(6 * (y / H))
        d.line([(0, y), (W, y)], fill=(BG[0] + shade, BG[1] + shade, BG[2] + shade + 2))
    d.ellipse([-260, -320, 460, 260], fill=(24, 20, 46))
    d.ellipse([W - 380, H - 300, W + 260, H + 260], fill=(16, 26, 30))
    return img


def wrap(draw, text, fnt, max_w):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def title_card():
    img = base_canvas()
    d = ImageDraw.Draw(img)
    f_big = font("seguisb.ttf", 104)
    f_tag = font("segoeui.ttf", 30)
    f_sub = font("segoeui.ttf", 22)

    d.text((W // 2, 250), "EscrowCourt", font=f_big, fill=TEXT, anchor="mm")
    d.text((W // 2, 336), "Milestone escrow where the acceptance criteria are the judge",
           font=f_tag, fill=MUTED, anchor="mm")
    d.line([(W // 2 - 90, 388), (W // 2 + 90, 388)], fill=ACCENT, width=4)
    d.text((W // 2, 440), "GenLayer Intelligent Contract  ·  studionet", font=f_sub,
           fill=GREEN, anchor="mm")
    d.text((W // 2, 490), "The model classifies. The contract decides the money.", font=f_sub,
           fill=MUTED, anchor="mm")
    return img


def shot_card(step, title, subtitle, shot):
    img = base_canvas()
    d = ImageDraw.Draw(img)

    f_step = font("seguisb.ttf", 20)
    f_title = font("seguisb.ttf", 38)
    f_sub = font("segoeui.ttf", 21)

    d.rounded_rectangle([70, 44, 70 + 58, 44 + 34], radius=17, fill=ACCENT)
    d.text((70 + 29, 44 + 17), f"0{step}", font=f_step, fill=(255, 255, 255), anchor="mm")
    d.text((148, 50), title, font=f_title, fill=TEXT, anchor="lm")

    for i, line in enumerate(wrap(d, subtitle, f_sub, W - 160)[:2]):
        d.text((72, 104 + i * 30), line, font=f_sub, fill=MUTED)

    src = Image.open(os.path.join(SHOTS, shot)).convert("RGB")
    max_w, max_h = 620, 470
    scale = min(max_w / src.width, max_h / src.height)
    src = src.resize((int(src.width * scale), int(src.height * scale)), Image.LANCZOS)

    px, py = 70, 180
    d.rounded_rectangle([px - 2, py - 2, px + src.width + 2, py + src.height + 2],
                        radius=12, outline=BORDER, width=2)
    img.paste(src, (px, py))

    tx = px + src.width + 46
    tw = W - tx - 70
    f_h = font("seguisb.ttf", 24)
    f_b = font("segoeui.ttf", 22)

    bullets = BULLETS[step]
    y = 200
    for head, body in bullets:
        d.ellipse([tx, y + 8, tx + 9, y + 17], fill=GREEN)
        d.text((tx + 24, y), head, font=f_h, fill=TEXT)
        y += 36
        for line in wrap(d, body, f_b, tw - 24):
            d.text((tx + 24, y), line, font=f_b, fill=MUTED)
            y += 29
        y += 22
    return img


def end_card():
    img = base_canvas()
    d = ImageDraw.Draw(img)
    f_big = font("seguisb.ttf", 62)
    f_lab = font("seguisb.ttf", 20)
    f_val = font("segoeui.ttf", 25)

    d.text((W // 2, 108), "EscrowCourt", font=f_big, fill=TEXT, anchor="mm")
    d.text((W // 2, 168), "Live on studionet — every step verifiable on-chain",
           font=f_val, fill=MUTED, anchor="mm")

    rows = [
        ("REPOSITORY", "github.com/God-jia/genlayer-escrowcourt"),
        ("dApp", "god-jia.github.io/genlayer-escrowcourt"),
        ("CONTRACT", "0x8A51ca7d8C77859E72DC89d673Ac9A665DcE66F3"),
        ("NETWORK", "studionet  ·  chain ID 61999"),
    ]
    y = 250
    for label, value in rows:
        d.rounded_rectangle([190, y, W - 190, y + 78], radius=12, fill=PANEL,
                            outline=BORDER, width=1)
        d.text((222, y + 20), label, font=f_lab, fill=ACCENT)
        d.text((222, y + 46), value, font=f_val, fill=TEXT)
        y += 96

    d.text((W // 2, H - 44), "28 direct-mode tests  ·  payable escrow  ·  real GEN payout",
           font=f_lab, fill=MUTED, anchor="mm")
    return img


BULLETS = {
    1: [
        ("Opening a job funds the escrow",
         "create_job is payable: the client sends exactly the escrow amount with the transaction and the contract holds the GEN."),
        ("The brief is frozen on-chain",
         "Brief, deliverable location and weighted milestones are stored with the job, so the standard cannot drift after delivery."),
    ],
    2: [
        ("One job, read back from studionet",
         "Job #0 loaded straight from the contract: client, freelancer, escrow amount and both milestones."),
        ("The contract really holds the GEN",
         "The funded amount sits in contract state until a milestone settles — no off-chain bookkeeping."),
    ],
    3: [
        ("Anyone can trigger the round",
         "A disputed milestone is handed to the validators; the trigger is permissionless."),
        ("Validators read the live deliverable",
         "gl.nondet.web.render fetches the page and the evidence before any verdict is formed."),
    ],
    4: [
        ("A verdict per criterion",
         "The model labels each criterion met / unmet / unclear — it never picks a number."),
        ("The split is derived in code",
         "One unclear and two unmet map deterministically to split: freelancer 1e14 wei, client 5e14 wei."),
    ],
    5: [
        ("Settled shares become withdrawable",
         "Balances are read straight from contract state, and the payee pulls them out with withdraw()."),
        ("withdraw() emits a real transfer",
         "Every payout leaves the contract as a real GEN transfer to the payee's account."),
    ],
}


def to_array(img):
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def build():
    slides = [title_card()]
    slides.append(shot_card(1, "Post a job, freeze the standard",
                            "Post a job tab — brief, deliverable location, milestones and the escrow sent with the transaction.",
                            "escrow-1-post.jpg"))
    slides.append(shot_card(2, "The job as the chain sees it",
                            "Job workspace — job #0 loaded live from studionet.",
                            "escrow-2-workspace.jpg"))
    slides.append(shot_card(3, "Hand a dispute to the validators",
                            "Adjudicate tab — permissionless trigger of the validator round.",
                            "escrow-3-adjudicate.jpg"))
    slides.append(shot_card(4, "Verdicts in, settlement out",
                            "Ruling — criteria classified unclear / unmet / unmet, split derived in code.",
                            "escrow-5-ruling.jpg"))
    slides.append(shot_card(5, "Real GEN in, real GEN out",
                            "Track record — withdrawable balance, escrow held by the contract and per-address reputation.",
                            "escrow-4-track.jpg"))
    slides.append(end_card())

    hold = int(HOLD * FPS)
    fade = int(FADE * FPS)

    writer = cv2.VideoWriter(OUT, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    if not writer.isOpened():
        raise SystemExit("VideoWriter could not open")

    frames = [to_array(s) for s in slides]
    for i, frame in enumerate(frames):
        for _ in range(hold - (fade if i < len(frames) - 1 else 0)):
            writer.write(frame)
        if i < len(frames) - 1:
            nxt = frames[i + 1]
            for k in range(fade):
                a = (k + 1) / (fade + 1)
                blended = cv2.addWeighted(frame, 1 - a, nxt, a, 0)
                writer.write(blended)
    writer.release()
    print("wrote", OUT)


if __name__ == "__main__":
    build()
