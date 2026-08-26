import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.services.fonts import BODY, BODY_BOLD, ensure_fonts_registered

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "Examflow_Deployment_Guide.pdf")

BLUE = colors.HexColor("#2563eb")
DARK = colors.HexColor("#111827")
GREY = colors.HexColor("#475569")
BOXBG = colors.HexColor("#f1f5f9")
GREEN = colors.HexColor("#166534")
GREENBG = colors.HexColor("#dcfce7")


def build():
    ensure_fonts_registered()
    doc = SimpleDocTemplate(
        OUTPUT_PATH,
        pagesize=A4,
        leftMargin=2.2 * cm,
        rightMargin=2.2 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        title="Examflow Deployment Guide",
    )

    title_style = ParagraphStyle("title", fontName=BODY_BOLD, fontSize=26, textColor=DARK, spaceAfter=6)
    subtitle_style = ParagraphStyle("subtitle", fontName=BODY, fontSize=13, textColor=GREY, spaceAfter=20)
    h1 = ParagraphStyle("h1", fontName=BODY_BOLD, fontSize=17, textColor=BLUE, spaceBefore=18, spaceAfter=10)
    h2 = ParagraphStyle("h2", fontName=BODY_BOLD, fontSize=12.5, textColor=DARK, spaceBefore=12, spaceAfter=6)
    body = ParagraphStyle("body", fontName=BODY, fontSize=10, leading=15, spaceAfter=8, textColor=DARK)
    step = ParagraphStyle("step", fontName=BODY, fontSize=10, leading=15, spaceAfter=6, textColor=DARK)
    note = ParagraphStyle("note", fontName=BODY, fontSize=9.5, leading=14, textColor=GREY, spaceAfter=8, leftIndent=6)
    code = ParagraphStyle(
        "code", fontName="Courier", fontSize=9.5, leading=14, textColor=DARK, backColor=BOXBG,
        borderPadding=8, spaceAfter=10, spaceBefore=2,
    )
    important = ParagraphStyle(
        "important", fontName=BODY_BOLD, fontSize=10, leading=15, textColor=colors.HexColor("#991b1b"),
        backColor=colors.HexColor("#fee2e2"), borderPadding=8, spaceAfter=10, spaceBefore=4,
    )
    tip = ParagraphStyle(
        "tip", fontName=BODY, fontSize=10, leading=15, textColor=GREEN,
        backColor=GREENBG, borderPadding=8, spaceAfter=10, spaceBefore=4,
    )
    toc_style = ParagraphStyle("toc", fontName=BODY, fontSize=10.5, leading=20, textColor=DARK)

    story = []

    # ---------- Cover ----------
    story.append(Spacer(1, 3 * cm))
    brand_style = ParagraphStyle("brand", fontName=BODY_BOLD, fontSize=40, leading=48, textColor=BLUE, spaceAfter=14)
    story.append(Paragraph("Examflow", brand_style))
    story.append(Spacer(1, 4))
    title_style.leading = 32
    story.append(Paragraph("Deployment Guide", title_style))
    story.append(Spacer(1, 10))
    subtitle_style.leading = 18
    story.append(Paragraph(
        "A complete, step-by-step guide to putting your hall ticket and attendance system online — "
        "written assuming you have no technical background. Follow it top to bottom in order.",
        subtitle_style,
    ))
    story.append(Spacer(1, 1 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0")))
    story.append(Spacer(1, 0.5 * cm))

    quick = [
        ("Where do I deploy this?", "Render.com for the website + backend, and Neon.tech for the database — both free."),
        ("Do I need Vercel?", "No. Vercel can't run this app's backend or database — Render does everything else in one place."),
        ("Do I need to buy a domain (DNS)?", "No. Render gives you free working web addresses with security (HTTPS) built in."),
        ("How do students get emailed?", "Through your Gmail/Google Workspace account, using a special \"app password\" (Part 1)."),
        ("How much will it cost?", "$0/month — since you send emails in weekly bursts rather than continuously, the free tiers fit your usage perfectly (see \"A note on cost\" below)."),
    ]
    qt_data = [[Paragraph(f"<b>{q}</b>", body), Paragraph(a, body)] for q, a in quick]
    qt = Table(qt_data, colWidths=[6.5 * cm, 8.5 * cm])
    qt.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.75, colors.HexColor("#e2e8f0")),
        ("BACKGROUND", (0, 0), (0, -1), BOXBG),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(Paragraph("Your questions, answered up front", h2))
    story.append(qt)
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "<b>A note on cost:</b> you mentioned you'll send your ~1200 emails in a weekly burst rather than "
        "continuously — so this guide uses free tiers throughout instead of \"always-on\" paid ones. The "
        "only tradeoff: if nobody's used the site in the last 15 minutes, the next visit takes about 30-60 "
        "seconds to \"wake up\" before responding. For a once-a-week pattern, that's a minor one-time wait, "
        "not a real cost. Open the dashboard a couple of minutes before you start scanning or sending "
        "emails each week to avoid even that.",
        tip,
    ))
    story.append(PageBreak())

    # ---------- Table of contents ----------
    story.append(Paragraph("What's in this guide", h1))
    toc_items = [
        "Part 0 — What you'll need before starting",
        "Part 1 — Set up Gmail so emails actually send",
        "Part 2 — Put your project on GitHub",
        "Part 3 — Create your Render account",
        "Part 4 — Create the database",
        "Part 5 — Deploy the backend (the \"engine\")",
        "Part 6 — Deploy the two websites (admin + scanner)",
        "Part 7 — Passwords to use (copy these in)",
        "Part 8 — First-time setup after deployment",
        "Part 9 — Exam day checklist",
        "Part 10 — If something goes wrong",
        "Appendix — Using your own domain name (optional)",
    ]
    story.append(ListFlowable(
        [ListItem(Paragraph(t, toc_style), spaceAfter=4) for t in toc_items],
        bulletType="1", start="1", leftIndent=18,
    ))
    story.append(PageBreak())

    def h1p(text):
        story.append(Paragraph(text, h1))

    def h2p(text):
        story.append(Paragraph(text, h2))

    def p(text):
        story.append(Paragraph(text, body))

    def steps(items):
        story.append(ListFlowable(
            [ListItem(Paragraph(t, step), spaceAfter=6) for t in items],
            bulletType="1", start="1", leftIndent=18,
        ))

    def bullets(items):
        story.append(ListFlowable(
            [ListItem(Paragraph(t, step), spaceAfter=4) for t in items],
            bulletType="bullet", leftIndent=18,
        ))

    def code_box(text):
        story.append(Paragraph(text.replace("\n", "<br/>"), code))

    def note_box(text):
        story.append(Paragraph(text, note))

    def warn_box(text):
        story.append(Paragraph("⚠ " + text, important))

    def tip_box(text):
        story.append(Paragraph("✓ " + text, tip))

    # ---------- Part 0 ----------
    h1p("Part 0 — What you'll need before starting")
    p("Gather these first so you're not stopping halfway through:")
    bullets([
        "A Gmail address, or better, a <b>Google Workspace</b> account (you mentioned you have one) — this is what will send the 1200 hall ticket emails.",
        "About 30–45 minutes of uninterrupted time.",
        "A working internet connection and a web browser (Chrome or Edge).",
        "This project's files, sitting in this folder on your computer — you don't need to touch the code itself, just follow the steps below.",
    ])
    note_box(
        "Everywhere in this guide you see a grey box like the one below, it's something to copy and paste exactly "
        "as shown — don't retype it by hand, small typos in these will stop things from working."
    )
    code_box("Example of a copy-paste box")

    # ---------- Part 1: Gmail ----------
    h1p("Part 1 — Set up Gmail so emails actually send")
    p(
        "Gmail will not let this app log in with your normal password — Google requires a special "
        "16-character \"App Password\" for anything other than a human typing into gmail.com. This only "
        "takes about 5 minutes."
    )
    h2p("Step 1.1 — Turn on 2-Step Verification (if it isn't on already)")
    steps([
        "Go to <b>myaccount.google.com/security</b> in your browser, signed in as the account you'll send emails from.",
        "Find \"2-Step Verification\" and turn it on if it says \"Off\". Follow Google's prompts (usually a code sent to your phone).",
        "If it already says \"On\", skip to Step 1.2.",
    ])
    h2p("Step 1.2 — Create an App Password")
    steps([
        "Go to <b>myaccount.google.com/apppasswords</b> (you may need to sign in again).",
        "Under \"App name\", type <b>Examflow</b> and click <b>Create</b>.",
        "Google will show you a 16-character password like <font face=\"Courier\">abcd efgh ijkl mnop</font>. "
        "<b>Copy it down somewhere safe right now</b> — Google only shows it once.",
        "Remove the spaces when you use it later, so it becomes one long word, e.g. <font face=\"Courier\">abcdefghijklmnop</font>.",
    ])
    warn_box(
        "This app password is not your Gmail password — it's a separate secret code just for this app. "
        "Never share it, and don't confuse it with your normal Google sign-in password."
    )
    note_box(
        "If your Google account is managed by a school/company (Workspace) and you don't see the "
        "\"App Passwords\" option, ask whoever manages that Google Workspace to enable it for your account, "
        "or to enable 2-Step Verification first."
    )
    tip_box(
        "Write down your Gmail address and this app password now — you'll paste both into Render in Part 5."
    )

    # ---------- Part 2: GitHub ----------
    h1p("Part 2 — Put your project on GitHub")
    p(
        "GitHub is a free place to store your project's code online. Render (where we're deploying) reads "
        "your code from there."
    )
    h2p("Step 2.1 — Create a GitHub account")
    steps([
        "Go to <b>github.com</b> and click <b>Sign up</b>. Use any email address and choose a username.",
        "Verify your email if asked.",
    ])
    h2p("Step 2.2 — Create an empty repository")
    steps([
        "Once signed in, click the <b>+</b> icon (top-right) → <b>New repository</b>.",
        "Name it <font face=\"Courier\">examflow</font>.",
        "Leave it set to <b>Private</b> (recommended, since this holds real student data) or Public — your choice.",
        "<b>Do not</b> check any of the boxes for README/gitignore/license — leave the repository completely empty.",
        "Click <b>Create repository</b>. GitHub will show you a page with a web address like "
        "<font face=\"Courier\">https://github.com/yourname/examflow.git</font> — copy that address.",
    ])
    tip_box(
        "If Claude is still available in your chat, the easiest option is to paste that GitHub address back "
        "into the conversation and ask Claude to push the code for you — it can run the technical commands "
        "directly. Otherwise, ask a technical friend to run <font face=\"Courier\">git push</font> for you "
        "using the address from Step 2.2."
    )

    # ---------- Part 3: Render account ----------
    h1p("Part 3 — Create your Render account")
    steps([
        "Go to <b>render.com</b> and click <b>Get Started</b>.",
        "Choose <b>Sign up with GitHub</b> — this links your GitHub account from Part 2 automatically, which "
        "makes every later step simpler.",
        "Approve the connection when GitHub asks.",
    ])
    note_box(
        "Render may ask for a payment card even for free services (common anti-abuse practice) — you should "
        "not be charged anything if you follow the Free tiers used in this guide. Please check Render's "
        "current pricing page, as this can change over time."
    )

    story.append(PageBreak())

    # ---------- Part 4: Database ----------
    h1p("Part 4 — Create the database")
    p(
        "This is where all student records, tickets, and attendance get stored. We're using a separate "
        "free service called <b>Neon</b> for this instead of Render's own database product, because Neon's "
        "free tier never expires — Render's free database gets permanently deleted after 90 days, which "
        "would wipe out your student records."
    )
    h2p("Step 4.1 — Create your Neon account and database")
    steps([
        "Go to <b>neon.tech</b> and click <b>Sign up</b> (signing up with Google is quickest — no credit "
        "card required).",
        "Create a new project. Name: <font face=\"Courier\">examflow</font>. Choose a region close to your "
        "students (e.g. Singapore, if available).",
        "Once created, Neon shows you a <b>Connection string</b> that looks like "
        "<font face=\"Courier\">postgresql://user:password@ep-xxxx.region.aws.neon.tech/neondb?sslmode=require</font>. "
        "Copy the whole thing.",
    ])
    h2p("Step 4.2 — Adjust it slightly for this app")
    p(
        "This app needs one small change to that connection string before it will work: add "
        "<font face=\"Courier\">+psycopg2</font> right after <font face=\"Courier\">postgresql</font>. For example:"
    )
    code_box(
        "Neon gives you:\n"
        "postgresql://user:password@ep-xxxx.neon.tech/neondb?sslmode=require\n\n"
        "You paste this into Render instead:\n"
        "postgresql+psycopg2://user:password@ep-xxxx.neon.tech/neondb?sslmode=require"
    )
    warn_box(
        "Keep the <font face=\"Courier\">?sslmode=require</font> part at the end exactly as Neon gave it to "
        "you — without it, the connection will fail."
    )
    tip_box(
        "Neon's free database also \"sleeps\" after inactivity, like the backend does — but it wakes up in "
        "about 1 second on the next request, so in practice you won't notice this one at all."
    )

    # ---------- Part 5: Backend ----------
    h1p("Part 5 — Deploy the backend (the \"engine\")")
    p(
        "This is the part that actually generates tickets, checks QR codes, and sends emails. Everything "
        "else (the two websites) talks to this."
    )
    steps([
        "On your Render dashboard, click <b>New +</b> → <b>Web Service</b>.",
        "Choose <b>Build and deploy from a Git repository</b>, then select your <font face=\"Courier\">examflow</font> "
        "repository from Part 2 and click <b>Connect</b>.",
        "Name: <font face=\"Courier\">examflow-backend</font>",
        "Region: same one you picked for the database in Part 4.",
        "Root Directory: <font face=\"Courier\">backend</font>",
        "Runtime: Render should detect <b>Docker</b> automatically (because of the Dockerfile already in the "
        "project) — leave it as Docker.",
        "Instance Type: choose <b>Free</b>. Since you send emails in weekly bursts rather than continuously, "
        "the free tier's only real tradeoff — a ~30-60 second wake-up if nobody's used it in 15+ minutes — "
        "fits your usage fine. See Part 9 for how to avoid even that on exam day.",
    ])
    h2p("Step 5.1 — Environment Variables")
    p(
        "Scroll down to \"Environment Variables\" on the same page and add each of the following one at a "
        "time (click <b>Add Environment Variable</b> for each row):"
    )

    env_rows = [
        ("DATABASE_URL", "Paste the adjusted Neon connection string from Part 4, Step 4.2."),
        ("JWT_SECRET_KEY", "eyJhbGciOiJIUzI1NiJ9-EXAMFLOW-2ZQmX9vLpR4tKdWnCsYhBjF7uAeGoTiVs"),
        ("JWT_ALGORITHM", "HS256"),
        ("JWT_EXPIRE_MINUTES", "720"),
        ("SMTP_HOST", "smtp.gmail.com"),
        ("SMTP_PORT", "587"),
        ("SMTP_USERNAME", "your Gmail/Workspace address from Part 1"),
        ("SMTP_APP_PASSWORD", "the 16-character app password from Part 1 (no spaces)"),
        ("SMTP_FROM_NAME", "Combine Mentor Official"),
        ("TICKET_STORAGE_DIR", "./storage/tickets"),
        ("ADMIN_DEFAULT_USERNAME", "admin"),
        ("ADMIN_DEFAULT_PASSWORD", "See Part 7 for the password to use here"),
    ]
    env_table = Table(
        [[Paragraph("<b>Name</b>", body), Paragraph("<b>Value</b>", body)]] +
        [[Paragraph(f"<font face='Courier'>{k}</font>", step), Paragraph(v, step)] for k, v in env_rows],
        colWidths=[5.2 * cm, 9.8 * cm],
    )
    env_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("BACKGROUND", (0, 0), (-1, 0), BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BOXBG]),
    ]))
    story.append(env_table)
    story.append(Spacer(1, 8))
    note_box(
        "The JWT_SECRET_KEY value above is a ready-to-use random secret generated specifically for this "
        "guide — you never need to type or remember it, just paste it in once."
    )
    p("Then:")
    steps([
        "Click <b>Create Web Service</b> at the bottom. Render will now build and start your backend — this "
        "takes 2–5 minutes the first time.",
        "Once it says <b>Live</b> (green), copy the web address shown at the top of the page — it looks like "
        "<font face=\"Courier\">https://examflow-backend.onrender.com</font>. You'll need this in Part 6.",
        "To check it worked: open that address in a browser with <font face=\"Courier\">/health</font> added "
        "to the end (e.g. <font face=\"Courier\">https://examflow-backend.onrender.com/health</font>) — you "
        "should see the text <font face=\"Courier\">{\"status\":\"ok\"}</font>.",
    ])
    tip_box(
        "No extra storage/disk purchase is needed — this app automatically re-creates a student's hall "
        "ticket file whenever it's needed, so nothing is lost if Render restarts the backend."
    )

    story.append(PageBreak())

    # ---------- Part 6: Frontends ----------
    h1p("Part 6 — Deploy the two websites (admin + scanner)")
    p(
        "These are the two things people actually click around in: the admin dashboard (for you) and the "
        "scanner (for the 10 teacher phones). Both are free to host on Render."
    )
    h2p("Step 6.1 — The Admin Dashboard")
    steps([
        "Click <b>New +</b> → <b>Static Site</b>.",
        "Select your <font face=\"Courier\">examflow</font> repository again.",
        "Name: <font face=\"Courier\">examflow-admin</font>",
        "Root Directory: <font face=\"Courier\">frontend-admin</font>",
        "Build Command: <font face=\"Courier\">npm install && npm run build</font>",
        "Publish Directory: <font face=\"Courier\">dist</font>",
        "Under Environment Variables, add one: Name <font face=\"Courier\">VITE_API_URL</font>, Value = the "
        "backend address you copied at the end of Part 5 (e.g. "
        "<font face=\"Courier\">https://examflow-backend.onrender.com</font>) — no trailing slash.",
        "Click <b>Create Static Site</b> and wait for it to build (1–3 minutes).",
        "Copy the resulting address, e.g. <font face=\"Courier\">https://examflow-admin.onrender.com</font> — "
        "this is the link you'll open to run your dashboard.",
    ])
    h2p("Step 6.2 — The Scanner (for teachers' phones)")
    p("Repeat the exact same steps as 6.1, with these differences:")
    steps([
        "Name: <font face=\"Courier\">examflow-scanner</font>",
        "Root Directory: <font face=\"Courier\">frontend-scanner</font>",
        "Same <font face=\"Courier\">VITE_API_URL</font> environment variable, same backend address as before.",
    ])
    tip_box(
        "Both of these addresses start with https:// automatically — this is exactly what lets a phone's "
        "browser grant camera access for scanning. You do not need to buy a domain name or set up DNS for "
        "any of this to work (see the Appendix if you'd like a custom domain anyway)."
    )
    warn_box(
        "VITE_API_URL only gets \"baked in\" when the site is built. If you ever change your backend's "
        "address later, you must update this variable and click \"Manual Deploy\" → \"Clear build cache & "
        "deploy\" on both the admin and scanner sites again."
    )

    # ---------- Part 7: Passwords ----------
    story.append(PageBreak())
    h1p("Part 7 — Passwords to use")
    p(
        "These are chosen to be realistic to remember while still being reasonably hard to guess. Feel free "
        "to swap in your own as long as each one mixes letters, a number, and a symbol."
    )
    pw_rows = [
        ("Admin dashboard login", "admin", "CMO@Exam2026!"),
        ("Teacher — Center A, Device 1", "centera.t1", "CenterA-T1@2026"),
        ("Teacher — Center A, Device 2", "centera.t2", "CenterA-T2@2026"),
        ("Teacher — Center A, Device 3", "centera.t3", "CenterA-T3@2026"),
        ("Teacher — Center A, Device 4", "centera.t4", "CenterA-T4@2026"),
        ("Teacher — Center A, Device 5", "centera.t5", "CenterA-T5@2026"),
        ("Teacher — Center B, Device 1", "centerb.t1", "CenterB-T1@2026"),
        ("Teacher — Center B, Device 2", "centerb.t2", "CenterB-T2@2026"),
        ("Teacher — Center B, Device 3", "centerb.t3", "CenterB-T3@2026"),
        ("Teacher — Center B, Device 4", "centerb.t4", "CenterB-T4@2026"),
        ("Teacher — Center B, Device 5", "centerb.t5", "CenterB-T5@2026"),
    ]
    pw_table = Table(
        [[Paragraph("<b>Account</b>", body), Paragraph("<b>Username</b>", body), Paragraph("<b>Password</b>", body)]] +
        [[Paragraph(a, step), Paragraph(f"<font face='Courier'>{u}</font>", step), Paragraph(f"<font face='Courier'>{pw}</font>", step)] for a, u, pw in pw_rows],
        colWidths=[6 * cm, 4 * cm, 5 * cm],
    )
    pw_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("BACKGROUND", (0, 0), (-1, 0), BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BOXBG]),
    ]))
    story.append(pw_table)
    story.append(Spacer(1, 8))
    p("<b>Where each password goes:</b>")
    bullets([
        "<b>Admin password</b> → paste into <font face=\"Courier\">ADMIN_DEFAULT_PASSWORD</font> in Part 5 "
        "before you first create the backend. This becomes your permanent login for the dashboard.",
        "<b>Teacher passwords</b> → you create these yourself, one at a time, from inside the admin dashboard "
        "after everything is deployed (see Part 8, Step 8.2) — you type these exact values in there, along "
        "with each teacher's real name and which center they belong to.",
    ])
    warn_box(
        "Change the admin password to something only you know if you ever suspect it's been seen by someone "
        "else — you can do this any time by changing ADMIN_DEFAULT_PASSWORD on Render and restarting the "
        "backend, though note this only changes it if the account doesn't already exist; ask Claude for help "
        "if you need to reset an existing password."
    )

    # ---------- Part 8: First-time setup ----------
    story.append(PageBreak())
    h1p("Part 8 — First-time setup after deployment")
    h2p("Step 8.1 — Log in")
    steps([
        "Open your admin website address from Part 6 (e.g. <font face=\"Courier\">https://examflow-admin.onrender.com</font>).",
        "Log in with username <font face=\"Courier\">admin</font> and the password you set in Part 7.",
    ])
    h2p("Step 8.2 — Create your 10 teacher accounts")
    steps([
        "Scroll to \"Teacher Devices / Accounts\" → \"Add Teacher\".",
        "For each of the 10 rows in the Part 7 table: enter the username, the teacher's real full name, the "
        "password, and pick their exam center from the dropdown. Click <b>Add</b>.",
        "Do this 10 times (5 for each center).",
    ])
    h2p("Step 8.3 — Do a small test run before the real thing")
    steps([
        "Prepare a tiny Excel sheet with just 2–3 of your own email addresses instead of real students, with "
        "columns: <b>Student Name</b>, <b>Email</b>, <b>Mobile Number</b>.",
        "Upload it, pick a center, click <b>Generate Hall Tickets</b>, then <b>Send Emails</b>.",
        "Check that the email actually arrives (including checking your Spam folder) with a working PDF "
        "attached and a scannable QR code, before uploading your real 1200 students.",
    ])
    h2p("Step 8.4 — Upload your real students")
    steps([
        "Prepare your real Excel sheet(s) — one upload per exam center, each with columns <b>Student Name</b>, "
        "<b>Email</b>, <b>Mobile Number</b>.",
        "Upload each sheet, picking the correct center each time.",
        "Click <b>Generate Hall Tickets</b> — with ~1200 students this can take a couple of minutes; it's "
        "safe to leave the page and check back, the dashboard will show progress and update automatically.",
        "Click <b>Send Emails</b> — this can take longer since it emails one by one; again, safe to leave "
        "and come back. Check the Students table afterward for anyone marked \"Failed\" and click Send "
        "Emails again to retry just those (it automatically skips anyone already sent).",
    ])
    tip_box(
        "A Google Workspace account can send about 2000 emails a day, so all 1200 students fit comfortably "
        "in a single day."
    )

    # ---------- Part 9: Exam day ----------
    story.append(PageBreak())
    h1p("Part 9 — Exam day checklist")
    tip_box(
        "About 5 minutes before scanning starts, open your admin dashboard address once yourself (or visit "
        "your backend address with <font face=\"Courier\">/health</font> added to the end) — this \"wakes up\" "
        "the free backend so the very first student isn't kept waiting."
    )
    bullets([
        "Each of the 10 teachers opens the scanner website address from Part 6 on their own phone's browser.",
        "Each logs in with their own username/password from Part 7.",
        "The browser will ask for camera permission — teachers must tap <b>Allow</b>.",
        "Students bring their <b>printed</b> hall ticket (the emailed PDF); the teacher points their phone's "
        "camera at the QR code on it.",
        "Green screen = checked in successfully. Red screen = already scanned today, or wrong exam center — "
        "the message on screen explains which.",
        "You (admin) can watch live attendance numbers update on your dashboard's \"Live Attendance\" and "
        "\"Attendance\" sections from anywhere, on any device.",
    ])

    # ---------- Part 10: Troubleshooting ----------
    h1p("Part 10 — If something goes wrong")
    trouble = [
        ("The site feels stuck or times out the first time", "This is the free tier waking up (see Part 9's tip box) — wait 30-60 seconds and try again; it will be fast for the rest of that session."),
        ("Emails aren't sending / show \"Failed\"", "Double-check SMTP_USERNAME and SMTP_APP_PASSWORD on Render exactly match Part 1 (no spaces in the app password), then restart the backend service (Render dashboard → your backend → Manual Deploy → Deploy latest commit)."),
        ("Camera won't open on a teacher's phone", "Make sure they're using the https:// scanner address from Render (not typed manually), and that they tapped Allow when asked for camera permission. Try closing and reopening the browser tab."),
        ("Dashboard shows a blank page or errors", "Check that VITE_API_URL on both frontend-admin and frontend-scanner exactly matches your backend's address, then redeploy both (see the warning box at the end of Part 6)."),
        ("A specific student didn't get their ticket", "Search for them in the Students table on the dashboard — check their Ticket and Email Status columns, and click Send Emails again if it shows Failed."),
        ("Something else / not covered here", "Come back to this Claude Code conversation, describe exactly what you're seeing, and Claude can look at the actual error logs on Render with you."),
    ]
    tr_table = Table(
        [[Paragraph("<b>Problem</b>", body), Paragraph("<b>What to do</b>", body)]] +
        [[Paragraph(a, step), Paragraph(b_, step)] for a, b_ in trouble],
        colWidths=[5.5 * cm, 9.5 * cm],
    )
    tr_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("BACKGROUND", (0, 0), (-1, 0), BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BOXBG]),
    ]))
    story.append(tr_table)

    # ---------- Appendix ----------
    story.append(PageBreak())
    h1p("Appendix — Using your own domain name (optional)")
    p(
        "This is entirely optional — everything above works perfectly using the free "
        "<font face=\"Courier\">.onrender.com</font> addresses. Only do this if you specifically want an "
        "address like <font face=\"Courier\">admin.yourcollege.com</font> instead."
    )
    steps([
        "Buy a domain name from any registrar (e.g. Namecheap, GoDaddy) — typically $10–15/year.",
        "On Render, open your admin (or scanner) static site → Settings → Custom Domains → Add Custom Domain, "
        "and enter the address you want.",
        "Render will show you one or two DNS records (usually a \"CNAME\") to add — copy these into your "
        "domain registrar's DNS settings page (each registrar's dashboard looks slightly different; their "
        "support articles walk through \"adding a CNAME record\").",
        "Wait 10 minutes to a few hours for it to activate — Render will show a green checkmark when it's live.",
    ])
    note_box("DNS is the system that connects a domain name to Render's address — you only need to think about it at all if you choose to do this optional step.")

    story.append(Spacer(1, 1 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0")))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        "Generated for the Examflow project — Combine Mentor Official.",
        ParagraphStyle("footer", fontName=BODY, fontSize=9, textColor=GREY),
    ))

    doc.build(story)
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    build()
