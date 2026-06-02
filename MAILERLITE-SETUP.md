# MailerLite Email Capture Setup — NZ Gym Guide

This document explains how MailerLite email capture is implemented across NZ Gym Guide and how to add new forms.

## Overview

MailerLite forms are embedded on pages using the MailerLite form embed script. Forms are referenced by `mailerlite_form_id` in content JSON files and rendered in templates using the `data-mailerlite-form` attribute.

## Current Implementation

### Setup in Templates

**File:** `layouts/base.html`

The MailerLite script is loaded globally in the base layout:

```html
<!-- MailerLite Email Capture Script -->
<script>
  (function() {
    var script = document.createElement('script');
    script.src = 'https://assets.mailerlite.com/js/form-embed.min.js';
    script.onload = function() {
      if (window.mailerlite && window.mailerlite.load) {
        window.mailerlite.load();
      }
    };
    document.body.appendChild(script);
  })();
</script>
```

This ensures all MailerLite forms can be embedded on any page.

### Setup in Guide Pages

**File:** `layouts/guide.html`

Guides can define an `email_capture` object in their JSON. If present, the following HTML is rendered:

```html
{% if guide.email_capture %}
<section class="section" style="background:linear-gradient(135deg,#f3e8ff,#e9d5ff);border-radius:var(--radius);">
  <div style="max-width:640px;margin:0 auto;text-align:center;">
    <h2>{{ guide.email_capture.heading }}</h2>
    <p>{{ guide.email_capture.body }}</p>
    <div data-mailerlite-form="{{ guide.email_capture.mailerlite_form_id }}"></div>
  </div>
</section>
{% endif %}
```

## How to Add Email Capture to a Guide

### Step 1: Create a Form in MailerLite

1. Log in to [MailerLite.com](https://mailerlite.com) → Dashboard
2. Go to **Forms** → **Create Form** (or Edit if already exists)
3. Create a new form with:
   - **Form name:** matching the form ID (e.g., "gym-deals-weekly")
   - **Type:** Embedded form
   - **Fields:** Email (required), optional: Name
   - **Design:** Simple, single-field email capture
4. Copy the **form ID** (visible in form settings)

### Step 2: Add to Guide JSON

In your guide's JSON file (e.g., `content/guides/nz-gym-discount-codes-2026.json`), add:

```json
{
  "slug": "nz-gym-discount-codes-2026",
  "title": "...",
  "email_capture": {
    "heading": "Get New Gym Deals Emailed to You Weekly",
    "body": "New deals and discount codes get added every Friday. Subscribe below...",
    "mailerlite_form_id": "gym-deals-weekly",
    "form_text": "Your email address",
    "form_cta": "Email me weekly deals",
    "show_on_scroll": true,
    "scroll_percentage": 50
  }
}
```

**Fields:**
- `heading` — H2 title above the form (required)
- `body` — Description paragraph (required)
- `mailerlite_form_id` — Form ID from MailerLite (required)
- `form_text` — Placeholder text in email field (optional, not used by MailerLite embed)
- `form_cta` — Button text (optional, controlled by MailerLite form design)
- `show_on_scroll` — Whether to show on scroll trigger (optional, future feature)
- `scroll_percentage` — When to trigger on scroll (optional, future feature)

### Step 3: Rebuild the Site

```bash
cd /home/ben/nz-gym-guide
python3 build.py
```

The guide page will now include the email capture form in the output HTML.

## Current Email Capture Forms

### Gym Deals (nz-gym-guide)

| Form Name | Form ID | URL | Purpose |
|-----------|---------|-----|---------|
| Gym Deals Weekly | `gym-deals-weekly` | /guides/nz-gym-discount-codes-2026/ | Weekly gym deal updates |

**Setup date:** June 2026

## Testing

1. **Local testing:** Run `python3 build.py` and open the output HTML in a browser
2. **Check the form loads:** Inspect the page source for `<div data-mailerlite-form="gym-deals-weekly">`
3. **Test form submission:** Fill out the form and verify the email is captured in MailerLite

## Troubleshooting

### Form doesn't appear on page

- Check that `mailerlite_form_id` is spelled correctly in the guide JSON
- Verify the form ID matches exactly in MailerLite (case-sensitive)
- Clear browser cache (MailerLite script may be cached)
- Check browser console for JavaScript errors

### Form appears but doesn't submit

- Ensure MailerLite form is **published** in MailerLite dashboard
- Check that the email field is set to **required**
- Verify the form's submission action is set to a valid MailerLite audience

### Form styling looks wrong

- The form inherits MailerLite's default styling
- To customize, edit the form in MailerLite dashboard under **Design**
- The purple gradient background (#f3e8ff, #e9d5ff) can be changed in `layouts/guide.html`

## MailerLite Admin

**Account:** instituteofbba@gmail.com
**Dashboard:** https://app.mailerlite.com
**Audiences:** Create new audiences for each form/site (e.g., "NZ Gym Guide Deals")

## Adding Forms to Other Pages (Future)

To add email capture to non-guide pages:

1. Define the form in MailerLite
2. Add custom template code similar to guide.html:

```html
<div data-mailerlite-form="your-form-id"></div>
```

3. The MailerLite script will auto-load the form

## Links & Resources

- [MailerLite Form Embed Docs](https://mailerlite.com/features/landing-pages)
- [MailerLite API Docs](https://developers.mailerlite.com/)
- [MailerLite Dashboard](https://app.mailerlite.com/)
