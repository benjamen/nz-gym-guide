# MailerLite email capture

Email capture is **off until you add your MailerLite account ID**. Until then the site shows no signup strip and no
in-article signup boxes (they would collect nothing). The earlier setup loaded `form-embed.min.js`, a file that does
not exist on MailerLite's servers (it returns 404), so no form has ever worked.

## Turn it on

1. In MailerLite open **Forms**, create an **Embedded form**, and choose *Copy embed code*.
2. From that code take two values:
   - the account number in `ml('account', '1234567')`, and
   - the form code in `<div class="ml-embedded" data-form="aBcDeF"></div>`.
3. Put the account number in `data/site.json` as `mailerlite_account_id`. The universal embed script then loads on
   every page (`layouts/base.html`).
4. In an article's JSON, set `email_capture.mailerlite_form_id` to the form code. The box renders only when the account
   ID is set.
5. For the footer signup strip, set `newsletter_form_url` in `data/site.json` to a form action URL that accepts a
   POSTed `EMAIL` field (a MailerLite hosted form, for example). The strip is hidden while that is empty.
6. Run `python3 build.py`, check the form appears and a test signup arrives in MailerLite, then push.
