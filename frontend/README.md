# HVAC Lead Generation - Frontend

React frontend for the HVAC Lead Generation platform that pulls permit data from county governments and syncs qualified leads to The Summit.AI CRM.

## Features

- **County Management**: Add and manage multiple county connections with Accela credentials
- **Permit Pulling**: Pull HVAC permits from counties with flexible date range filtering
- **Lead Dashboard**: Review, filter, and select leads for CRM sync
- **Summit.AI Integration**: Batch sync selected leads to Summit.AI CRM
- **Real-time Status**: Track sync status with visual indicators

## Tech Stack

- React 19.2.0 with React DOM 19.2.0
- Vite 7.2.4 (build tool)
- React Router 7.9.6 (routing)
- TanStack React Query 5.90.11 (API state management)
- Axios 1.13.2 (HTTP client)
- TailwindCSS 4.1.17 (styling)
- Lucide React 0.555.0 (icons)
- date-fns 4.1.0 (date formatting)

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Backend API running on `http://localhost:8000`

### Installation

```bash
# Install dependencies
npm install

# Copy environment file
cp .env.example .env

# Start development server
npm run dev
```

The app will be available at `http://localhost:3000`

### Environment Variables

Create a `.env` file:

```
VITE_API_URL=http://localhost:8000
```

## Project Structure

```
frontend/
├── src/
│   ├── api/              # API client and endpoint definitions
│   │   ├── client.js     # Axios instance with interceptors
│   │   ├── counties.js   # County API calls
│   │   ├── permits.js    # Permit API calls
│   │   ├── leads.js      # Lead API calls
│   │   └── summit.js     # Summit.AI API calls
│   ├── components/       # React components
│   │   ├── Layout.jsx    # Main layout with navigation
│   │   ├── counties/     # County-related components
│   │   ├── leads/        # Lead-related components
│   │   └── settings/     # Settings components
│   ├── pages/            # Page components
│   │   ├── CountiesPage.jsx
│   │   ├── LeadsPage.jsx
│   │   └── SettingsPage.jsx
│   ├── hooks/            # Custom React hooks
│   │   ├── useCounties.js
│   │   ├── usePermits.js
│   │   └── useLeads.js
│   └── utils/            # Utility functions
│       └── formatters.js # Date, currency, number formatters
├── index.html
├── vite.config.js
└── tailwind.config.js
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## Key Features

### Counties Page
- View all configured counties with status indicators
- Add new counties with 3-step wizard (name → credentials → test)
- Pull permits with date range or "older than X years" filters
- Visual status: Connected, Token Expired, Error

### Leads Page
- Table view with filtering by county and sync status
- Checkbox selection for batch operations
- Send selected leads to Summit.AI
- Sync status badges: Pending, Synced, Failed

### Settings Page
- Configure Summit.AI API credentials
- Test connection before saving
- API key masking for security

## API Integration

The frontend communicates with the FastAPI backend using REST endpoints:

- `GET/POST /api/counties` - County management
- `POST /api/counties/{id}/pull-permits` - Pull permits from Accela
- `GET /api/leads` - Fetch leads with filters
- `POST /api/leads/sync-to-summit` - Sync leads to Summit.AI
- `GET/PUT /api/summit/config` - Summit.AI configuration

## Development

The app uses React Query for data fetching and caching. All API calls are wrapped in custom hooks for easy state management.

### Adding a New API Endpoint

1. Add the API call to the appropriate file in `src/api/`
2. Create or update a React Query hook in `src/hooks/`
3. Use the hook in your component

Example:
```javascript
// In component
const { data, isLoading, error } = useCounties();
```

## Building for Production

```bash
npm run build
```

The production build will be in the `dist/` directory, ready for deployment to Vercel or any static hosting service.

## License

Private - All Rights Reserved
