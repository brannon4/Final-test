# Pick & Profit MA — private iPhone web app

A mobile-friendly Streamlit app for Massachusetts pick-and-pull vehicle inventory research and eBay sold-comps profit estimates. **No engines, transmissions or differentials.**

## Security model
- **Fail closed:** app refuses to display inventory or analytics unless `APP_PASSWORD` is configured and the visitor signs in.
- HTTPS is provided by the cloud host. Keep the GitHub repository **private** and the password in the host's encrypted environment variables, never in source code.
- A public login endpoint remains reachable; **inventory and analytics are not publicly visible**. For network-level restriction, put Cloudflare Access or another identity-aware proxy in front of the service.
- Login is a single-owner password gate, not multi-user identity management or MFA. Choose a long unique password and do not share it. The app does not persist uploads or comps to a database: uploaded CSVs stay in the active session and must be reuploaded after restart.

## Deploy from a private GitHub repository to Render
1. Create a **private** repository on GitHub and upload the contents of this folder (including `render.yaml`). Do not upload secrets.
2. At Render, connect your GitHub account and choose **New > Blueprint**, selecting your private repository and `render.yaml`.
3. When prompted for `APP_PASSWORD`, enter a long, unique password. Choose a paid **Starter** web service if you need dependable access and no free-tier sleep.
4. After deployment, open the HTTPS URL on iPhone Safari. Sign in, then use **Share > Add to Home Screen**.
5. To change the password, update `APP_PASSWORD` in Render and redeploy/restart. This invalidates the old password for new sessions; existing signed-in sessions may remain active until they expire/restart.

## Local test
```bash
pip install -r requirements.txt
export APP_PASSWORD='choose-a-long-unique-password'
streamlit run app.py
```
On Windows PowerShell: `$env:APP_PASSWORD='choose-a-long-unique-password'`.

## Data and analytics
- Upload live vehicle inventory as CSV (`yard,year,make,model,trim,row,vin,arrival_date,source_url`). The bundled six vehicles are **dated sample data**, not a live feed.
- Upload verified sold transactions as CSV (`query,sold_price,shipping_charged,sold_date,condition,source_url`) and yard prices (`yard,part,price`).
- The app calculates median sold price, sample size, estimated profit and ROI. Without both inputs, it **does not invent profits**.
- eBay's sold-history Marketplace Insights API has restricted access. There is no live scraping or auto-sync in this build.
- Check OEM part number, condition, compatibility, and yard availability before purchasing.

## Operational caveats
- Streamlit Community Cloud's public app option is **not** the recommended deployment for a private owner-only workflow. Use a private repository and password-gated Render deployment.
- A password-gated public HTTPS endpoint is different from a network-private service. Add Cloudflare Access if you require pre-app authentication/MFA.
- Do not use the sample vehicle list as current inventory.
