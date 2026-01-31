# Ads Sync - Your Friendly Guide to Connecting Odoo with Meta Ads

Welcome to the Ads Sync module! If you're running Facebook or Instagram ads and using Odoo for your business, this guide will help you get the most out of connecting the two. We'll walk through everything step by step, with plenty of examples and tips to make it easy—even if you're not a tech expert.

*Last updated: January 28, 2026*

## Table of Contents
- [What is Ads Sync and Why Should You Care?](#what-is-ads-sync-and-why-should-you-care)
- [Key Features Made Simple](#key-features-made-simple)
- [Getting Started: Step-by-Step Setup](#getting-started-step-by-step-setup)
- [Understanding Events and Categories](#understanding-events-and-categories)
- [Exploring the Dashboard](#exploring-the-dashboard)
- [Advanced Features: Manual Pushing and Webhooks](#advanced-features-manual-pushing-and-webhooks)
- [Privacy and Security: What You Need to Know](#privacy-and-security-what-you-need-to-know)
- [Troubleshooting Common Issues](#troubleshooting-common-issues)
- [Best Practices for Success](#best-practices-for-success)
- [Frequently Asked Questions](#frequently-asked-questions)
- [Support and Resources](#support-and-resources)
- [Glossary of Terms](#glossary-of-terms)

---

## What is Ads Sync and Why Should You Care?

Imagine you're running ads on Facebook or Instagram to attract customers. Ads Sync acts like a bridge between your Odoo system (where you manage sales, leads, and orders) and Meta's advertising platform. It automatically shares key business events with Meta, helping your ads perform better and cost less.

### Why This Matters for Your Business
- **Smarter Targeting**: Meta learns who your best customers are and shows ads to similar people.
- **Accurate Measurement**: See which ads actually drive sales, not just clicks.
- **Save Money**: Better ads mean fewer wasted dollars on uninterested viewers.
- **Stay Compliant**: Data is sent securely and privately, following privacy rules.

**Real-World Example**: Sarah runs an online store selling handmade jewelry. Before Ads Sync, her ads reached many people but conversions were low. After connecting Odoo, Meta learned that buyers often start with a "Lead" event (like signing up for a newsletter) and end with a "Purchase." Now, her ads target similar jewelry lovers, boosting sales by 30% and cutting ad costs in half!

---

## Key Features Made Simple

Ads Sync is designed to be powerful yet easy to use. Here are the main features explained in plain English:

### 🎯 Automatic Event Tracking
No manual work needed! When something important happens in Odoo, Ads Sync tells Meta right away. For example:
- A new lead signs up → Meta knows someone is interested.
- A sale is completed → Meta celebrates a conversion!

This helps Meta optimize your ads automatically.

### 🔘 Easy On/Off Controls
Each type of event has a simple switch. Turn it ON to share that data with Meta, or OFF to keep it private. You control everything!

### 📊 Built-in Statistics
Keep track of what's happening:
- How many events have been sent (e.g., "45 leads shared").
- When the last event was sent.
- Whether it's working smoothly or if there are issues.

### 🧪 Test Mode for Peace of Mind
Before going live, use Test Mode to practice. It sends sample data to Meta so you can check everything works without affecting real ads.

**Visual Tip**: Picture a clean dashboard with colorful cards for each event. Green means "ON" and active; gray means "OFF." Hover over any card to see quick stats like "Last sent: 2 hours ago."

---

## Getting Started: Step-by-Step Setup

Let's get you up and running! This process takes about 15-20 minutes. No coding required—just follow these steps.

### Step 1: Gather Your Meta Credentials
First, you need two things from Meta (Facebook/Instagram):
- **Pixel ID**: Think of this as your ad account's unique ID. Find it in Meta Events Manager under "Data Sources" → "Pixels."
- **Access Token**: A special password for secure communication. Get it from Meta Events Manager → "Settings" → "Conversions API."

**Pro Tip**: If you're not sure where to find these, ask your marketing team or check Meta's help center. It's like getting a key to your front door—Meta needs it to let your data in safely.

### Step 2: Set Up Your Subscription in Odoo
1. Log into your Odoo admin panel.
2. Go to **Ads Sync** in the menu (you might need to install the module first—ask your IT team if it's not there).
3. Click **Subscriptions** → **Create**.
4. Fill in the form:
   - Name: Something simple like "My Meta Ads Connection"
   - Pixel ID: Paste the one you got from Meta.
   - Access Token: Paste the token.
5. Click **Save**. You'll see a success message if it's working.

**Screenshot Description**: The form looks like a simple web page with text boxes. At the top, there's a green checkmark if everything is connected correctly.

### Step 3: Choose Which Events to Enable
1. Navigate to **Ads Sync** → **Event Configuration**.
2. You'll see a colorful board with cards for different events, grouped by category (like "Sales" or "Leads").
3. For each event you want to track, click the toggle switch to turn it ON.
4. Start with essentials:
   - **Purchase**: Tracks when orders are confirmed (great for e-commerce).
   - **Lead**: Tracks new inquiries.
   - **CompleteRegistration**: Tracks new user sign-ups.

**Example**: If you sell products, turn on "Purchase" and "InitiateCheckout" to see the full buying journey—from interest to sale.

### Step 4: Test Everything Works
1. Pick one event (like "Lead") and enable its Test Mode (there's a checkbox for this).
2. In Odoo, create a test lead (e.g., add a fake customer inquiry).
3. Wait a few minutes, then check Meta Events Manager → "Test Events" to see if your test data arrived.
4. If it did, great! Turn off Test Mode and enable the event for real.

**What You'll See**: In Meta Events Manager, look for a new test event with details like "Lead created at [time]." If it's missing, double-check your Pixel ID.

---

## Understanding Events and Categories

Events are the "actions" Ads Sync shares with Meta. They're grouped into categories to make it easy. Here's a breakdown with examples:

### 📢 Lead Generation (For Sales-Focused Businesses)
Track your sales funnel from interest to deal.

| Event | What Triggers It | Why It Helps | Example |
|-------|------------------|--------------|---------|
| **Lead** | New lead created | Spots early interest | Someone fills out your contact form. |
| **QualifiedLead** | Lead becomes an opportunity | Identifies hot prospects | A lead is upgraded to a sales opportunity. |
| **ConvertedLead** | Deal is won | Celebrates wins | A quote is accepted and paid. |

**Best For**: B2B companies, consultants, or anyone with long sales cycles.

### 💰 Sales & Purchase (For E-Commerce and Retail)
Focus on actual money-moving events.

| Event | What Triggers It | Why It Helps | Example |
|-------|------------------|--------------|---------|
| **Purchase** | Order confirmed | Tracks revenue | Customer completes a $50 order. |
| **InitiateCheckout** | Quote sent | Shows intent | You email a price quote. |
| **AddPaymentInfo** | Invoice posted | Confirms commitment | An invoice is generated and sent. |

**Best For**: Online stores, restaurants, or product sellers.

### 👤 User Engagement (For Interaction-Heavy Businesses)
Monitor how people interact with your brand.

| Event | What Triggers It | Why It Helps | Example |
|-------|------------------|--------------|---------|
| **Contact** | New contact added | Builds audience | A visitor subscribes to your newsletter. |
| **Schedule** | Meeting booked | Tracks engagement | Someone schedules a demo call. |

**Best For**: Service providers, doctors, or appointment-based businesses.

### 📝 Registration & Subscription (For Membership Sites)
Track sign-ups and growth.

| Event | What Triggers It | Why It Helps | Example |
|-------|------------------|--------------|---------|
| **CompleteRegistration** | User signs up | Measures acquisition | New member joins your platform. |
| **Subscribe** | Newsletter sign-up | Grows email list | Visitor opts into your updates. |

**Best For**: SaaS apps, gyms, or content sites.

**Tip**: Don't enable everything at once. Start with 2-3 that match your business goals, like "Purchase" if sales are key.

---

## Exploring the Dashboard

The Ads Sync dashboard is your control center. It's designed like a visual board (think Trello or Kanban) for easy navigation.

### Main View: Event Configuration
- **Layout**: Events are in columns by category (e.g., "Lead Generation" on the left, "Sales" in the middle).
- **Cards**: Each event is a card with:
  - Name (e.g., "Purchase")
  - Toggle switch (ON/OFF)
  - Quick description
  - Stats: Push count (e.g., "128 sent") and last push date.

**Visual Example**:
```
[Lead Generation]     [Sales & Purchase]     [User Engagement]
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│ Lead       [ON] │   │ Purchase    [ON]│   │ Contact    [OFF]│
│ 📊 45 sent      │   │ 📊 128 sent     │   │                 │
│ Last: 1 hr ago  │   │ Last: 30 min ago│   │                 │
└─────────────────┘   └─────────────────┘   └─────────────────┘
```

### Statistics Panel
Click on any card for details:
- Total pushes
- Success rate
- Any errors

**Engaging Tip**: Watch the numbers grow as your business thrives—it's motivating to see "Purchase" events increase after a good ad campaign!

---

## Advanced Features: Manual Pushing and Webhooks

### Manual Event Pushing
Sometimes you need to send data manually (e.g., for testing or historical records).
1. Go to **Ads Sync** → **Event Push**.
2. Choose an event type (like "Purchase").
3. Fill in details (e.g., customer email, amount).
4. Click **Push Event**.
5. Check the response—green means success!

**Use Case**: Importing old sales data to give Meta a head start.

### Receiving Webhooks from Meta
Ads Sync can also receive data FROM Meta (like lead form submissions).
- **Setup**: Provide Meta with your webhook URL (e.g., `https://your-odoo.com/webhooks/meta`).
- **What Happens**: Meta sends data (e.g., a new lead from an ad), and Odoo creates a record automatically.

**Example**: A Facebook ad collects emails—Meta sends them to Odoo, creating instant leads.

**Visual Tip**: In Meta's setup, you'll paste the URL into a form. Odoo shows incoming webhooks in a log view.

---

## Privacy and Security: What You Need to Know

We take privacy seriously. Here's what happens to your data:

### What Gets Sent?
Only business data—no secrets!
- ✅ Hashed email/phone/name (scrambled so no one can read it)
- ✅ Sale amounts and products
- ❌ Passwords, notes, or sensitive info (never shared)

### How It's Protected
- **Hashing**: Data is turned into a code (like a secret recipe) that Meta can't reverse.
- **Encryption**: Everything travels over secure HTTPS.
- **Your Control**: You decide what to share with toggles.

**Example of Hashing**:
- Real email: `customer@example.com`
- What Meta sees: `a1b2c3d4...` (unreadable gibberish)

**Reassurance**: This follows privacy laws like GDPR. Meta uses the data to improve ads, not to spy.

---

## Troubleshooting Common Issues

Don't worry—most issues are easy to fix. Here's a guide:

### Problem: Events Aren't Sending
- **Check**: Is the event toggle ON? Subscription active?
- **Fix**: Go to Event Configuration and flip the switch. Restart Odoo if needed.
- **Test**: Use Test Mode to verify.

### Problem: Data Not Showing in Meta
- **Check**: Correct Pixel ID? Internet connection?
- **Fix**: Double-check credentials in Subscriptions. Wait 5-10 minutes—Meta processes data.
- **Tip**: Look in Meta Events Manager → "Events" tab for arrivals.

### Problem: Connection Errors
- **Check**: Firewall blocking HTTPS? Server offline?
- **Fix**: Ensure outbound internet access. Contact your IT for firewall rules.
- **Example Error**: "Network timeout" → Check your server's internet.

### Problem: Webhooks Not Working
- **Check**: URL correct? Meta verified it?
- **Fix**: Regenerate the URL in Odoo and update Meta.

**General Advice**: Check Odoo logs (ask your admin) for messages like "[MetaEventConfig] Error." Start with one event to isolate issues.

---

## Best Practices for Success

### Start Small and Scale
1. Enable 2-3 key events (e.g., Purchase and Lead).
2. Test in Meta for a week.
3. Add more as you get comfortable.

### Focus on What Matters
Prioritize revenue-driving events:
- E-commerce: Purchase, InitiateCheckout
- B2B: Lead, ConvertedLead

### Always Test First
Use Test Mode before live data. It's like a dress rehearsal!

### Monitor Regularly
Weekly check: Are push counts increasing? Any errors? Compare with Meta's reports.

**Success Story**: A small business owner enabled Ads Sync, focused on "Purchase" events, and saw ad costs drop 25% within a month. "It felt like having a smart assistant optimizing my ads!"

---

## Frequently Asked Questions

**Q: Will this slow down my Odoo?**  
A: Nope! Events send in the background, so your daily work stays fast.

**Q: Can I send old data?**  
A: Yes, use Manual Event Push for historical records.

**Q: Do I need a developer?**  
A: Basic use is self-service. For setup, your IT team might help with credentials.

**Q: Is this safe for GDPR/privacy?**  
A: Data is hashed and you control sharing. Check with your legal team for specifics.

**Q: What if Meta changes their API?**  
A: The module uses a server that updates automatically—you're covered.

---

## Support and Resources

Need help?
1. Check Odoo's logs for clues.
2. Test with simple events first.
3. Contact your Odoo provider or developer.
4. Visit Meta's Ads Help Center for ad-side issues.

**Resources**:
- Meta Events Manager Guide
- Odoo Community Forums
- This guide's troubleshooting section

---

## Glossary of Terms

| Term | Simple Explanation |
|------|-------------------|
| **CAPI** | Meta's secure way to share data from servers (like Odoo). |
| **Pixel** | Your ad account's ID, like a username. |
| **Event** | An action we track, e.g., a sale. |
| **Webhook** | Meta sending data back to Odoo, like a notification. |
| **Hashing** | Scrambling data for privacy. |
| **Conversion** | A goal, like making a sale. |

---

Thanks for using Ads Sync! With this connection, your ads will work smarter, not harder. If you have feedback, let us know—we're here to help you succeed. 🚀
