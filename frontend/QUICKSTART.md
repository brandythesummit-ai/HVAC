# Quick Start Guide

## Prerequisites
- Node.js 18+ installed
- Backend API running on `http://localhost:8000` (optional for development)

## Setup (First Time)

```bash
cd /Users/Brandy/projects/HVAC/frontend

# Install dependencies
npm install

# Environment is already configured (.env file exists)
```

## Run Development Server

```bash
npm run dev
```

The app will start at: **http://localhost:3000**

## Available Commands

```bash
npm run dev      # Start development server (hot reload enabled)
npm run build    # Build for production
npm run preview  # Preview production build locally
npm run lint     # Run ESLint checks
```

## What You'll See

### 1. Counties Page (Default)
- Empty state with "Add County" button
- Once counties added, grid of county cards showing:
  - Status indicators (Connected/Token Expired/Error)
  - Last pull timestamp
  - "Pull Permits" button

### 2. Leads Page
- Filterable table of leads
- Select leads with checkboxes
- "Send to Summit.AI" button for batch sync

### 3. Settings Page
- Summit.AI API configuration
- Test connection functionality

## Backend API Not Ready?

The app will show error messages when API calls fail, but the UI is fully functional. You can:
- Navigate between all pages
- Open modals and forms
- See the UI design and interactions

## Common Issues

### Port 3000 Already in Use
```bash
# Kill the process using port 3000
lsof -ti:3000 | xargs kill -9

# Or change the port in vite.config.js
```

### Build Fails
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

## Next Steps

1. Ensure backend API is running
2. Add your first county via the UI
3. Configure Accela credentials
4. Pull permits from the county
5. Review leads in the Leads page
6. Configure Summit.AI in Settings
7. Sync leads to your CRM

## Production Build

```bash
npm run build
```

Output will be in `dist/` directory, ready for deployment to:
- Vercel
- Netlify
- Any static hosting service

## Environment Variables

Located in `.env`:
```
VITE_API_URL=http://localhost:8000
```

Change this when deploying to production to point to your production API.
