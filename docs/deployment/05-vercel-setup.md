# Vercel Frontend Deployment

> Step-by-step guide to deploy the React dashboard on Vercel.

---

## Overview

| Attribute | Value |
|-----------|-------|
| Platform | Vercel |
| Cost | Free (Hobby) / $20/mo (Pro) |
| Build Time | ~1-2 minutes |
| Global CDN | Yes (Edge Network) |

Vercel is ideal for the React frontend because:
- Free tier with generous limits
- Optimized for React applications
- Global CDN for fast loads
- Automatic HTTPS
- Preview deployments for PRs

---

## Prerequisites

- GitHub account with repository access
- Vercel account (free)
- Backend API deployed and running

---

## Step 1: Prepare Frontend

### Update Environment Configuration

**Create `dashboard/.env.production`:**

```bash
REACT_APP_API_URL=https://your-api-domain.com
```

Replace `your-api-domain.com` with your actual backend URL (Railway, Render, etc.).

### Verify Build Works Locally

```bash
cd dashboard
npm install
npm run build
```

Ensure build completes without errors.

---

## Step 2: Connect to Vercel

### Option A: Vercel Dashboard

1. Go to https://vercel.com
2. Sign up/login with GitHub
3. Click "Add New Project"
4. Import your GitHub repository
5. Configure project:

| Setting | Value |
|---------|-------|
| Framework Preset | Create React App |
| Root Directory | `dashboard` |
| Build Command | `npm run build` |
| Output Directory | `build` |

### Option B: Vercel CLI

```bash
# Install Vercel CLI
npm install -g vercel

# Login
vercel login

# Deploy from dashboard directory
cd dashboard
vercel

# Follow prompts:
# - Link to existing project? No
# - Project name: your-project-name
# - Directory: ./
# - Override settings? No
```

---

## Step 3: Configure Environment Variables

### In Vercel Dashboard

1. Go to Project Settings → Environment Variables
2. Add:

| Name | Value | Environment |
|------|-------|-------------|
| `REACT_APP_API_URL` | `https://your-api.railway.app` | Production |
| `REACT_APP_API_URL` | `https://your-api-staging.railway.app` | Preview |
| `REACT_APP_API_URL` | `http://localhost:8000` | Development |

### Via CLI

```bash
vercel env add REACT_APP_API_URL production
# Enter value when prompted
```

---

## Step 4: Configure Build Settings

### vercel.json (Optional)

Create `dashboard/vercel.json` for custom configuration:

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "build",
  "framework": "create-react-app",
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "X-Content-Type-Options",
          "value": "nosniff"
        },
        {
          "key": "X-Frame-Options",
          "value": "DENY"
        },
        {
          "key": "X-XSS-Protection",
          "value": "1; mode=block"
        }
      ]
    },
    {
      "source": "/static/(.*)",
      "headers": [
        {
          "key": "Cache-Control",
          "value": "public, max-age=31536000, immutable"
        }
      ]
    }
  ]
}
```

---

## Step 5: Deploy

### Automatic Deployments

After connecting to GitHub, Vercel automatically deploys:
- **Production**: On push to `main`/`master`
- **Preview**: On pull requests

### Manual Deploy

```bash
cd dashboard
vercel --prod
```

---

## Step 6: Custom Domain (Optional)

### Add Domain

1. Project Settings → Domains
2. Add your domain (e.g., `dashboard.example.com`)
3. Configure DNS:

| Type | Name | Value |
|------|------|-------|
| CNAME | dashboard | cname.vercel-dns.com |

Or for apex domain:
| Type | Name | Value |
|------|------|-------|
| A | @ | 76.76.21.21 |

### Verify Domain

Vercel automatically provisions SSL certificate.

```bash
# Check certificate
curl -I https://dashboard.example.com
```

---

## Configuration Reference

### Project Settings

| Setting | Recommended Value |
|---------|-------------------|
| Framework | Create React App |
| Node.js Version | 18.x |
| Build Command | `npm run build` |
| Output Directory | `build` |
| Install Command | `npm install` |

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `REACT_APP_API_URL` | Backend API URL | Yes |
| `REACT_APP_VERSION` | App version | No |

---

## Deployment Verification

### Check Deployment

```bash
# Open deployed site
vercel open

# Check deployment status
vercel ls
```

### Verify API Connection

1. Open browser developer tools (F12)
2. Go to Network tab
3. Refresh the dashboard
4. Verify API requests go to correct backend URL
5. Check for CORS errors

---

## Troubleshooting

### Build Fails

**TypeScript Errors:**
```bash
# Fix locally first
cd dashboard
npx tsc --noEmit
```

**Missing Dependencies:**
```bash
# Ensure all deps are in package.json
npm install
git add package.json package-lock.json
git commit -m "Update dependencies"
git push
```

### API Connection Fails

**CORS Errors:**
- Verify backend CORS allows Vercel domain
- Check `CORS_ORIGINS` includes `https://your-project.vercel.app`

**Wrong API URL:**
- Check environment variable in Vercel dashboard
- Redeploy after changing env vars

### Blank Page

**Check browser console for errors:**
- Missing env vars: Check `REACT_APP_API_URL`
- Routing issues: Ensure `vercel.json` has rewrite rules

---

## Performance Optimization

### Vercel Analytics

Enable in Project Settings → Analytics

### Caching

Static assets are automatically cached:
- `/static/*` - Immutable, 1 year cache
- HTML - No cache (always fresh)

### Edge Functions (Optional)

For advanced use cases, add Edge Functions for:
- A/B testing
- Geolocation-based content
- Authentication

---

## Cost Considerations

### Free Tier (Hobby)

| Resource | Limit |
|----------|-------|
| Bandwidth | 100GB/month |
| Builds | 6000 minutes/month |
| Serverless Functions | 100GB-hours |
| Team Members | 1 |

### Pro Tier ($20/month)

| Resource | Limit |
|----------|-------|
| Bandwidth | 1TB/month |
| Builds | Unlimited |
| Team Members | Unlimited |
| Analytics | Included |

For most personal projects, the free tier is sufficient.

---

## Alternative Frontend Hosts

If Vercel doesn't meet your needs:

| Platform | Free Tier | Notes |
|----------|-----------|-------|
| Netlify | 100GB bandwidth | Similar features |
| Cloudflare Pages | Unlimited bandwidth | Best performance |
| GitHub Pages | 100GB bandwidth | Basic static hosting |
| Render | 100GB bandwidth | Part of Render ecosystem |

---

## Checklist

### Before Deployment
- [ ] Build works locally (`npm run build`)
- [ ] No TypeScript errors (`npx tsc --noEmit`)
- [ ] Environment variables documented
- [ ] Backend API is accessible

### After Deployment
- [ ] Site loads correctly
- [ ] API connection works (no CORS errors)
- [ ] All pages accessible
- [ ] Data updates visible
- [ ] Custom domain configured (if applicable)

---

> **Back to:** [Overview](00-overview.md)
