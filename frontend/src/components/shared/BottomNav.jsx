import { NavLink } from 'react-router-dom';
import { Map as MapIcon, List as ListIcon, Calendar } from 'lucide-react';

/**
 * 3-tab bottom navigation for the mobile field-sales shell.
 *
 * Hidden at lg: and above (desktop has the sidebar). On mobile, this
 * is the only way to switch between the three core surfaces; the
 * left drawer (hamburger from MapTopBar / PageFiltersHeader) holds
 * settings/logout/secondary destinations.
 *
 * pb-[env(safe-area-inset-bottom)] keeps the nav above the iOS home
 * indicator. min-h-touch / min-w-touch on each tab guarantees ≥44px
 * tap targets per the plan's mobile affordance rules.
 */
const TABS = [
  { to: '/map',  icon: MapIcon,  label: 'Map' },
  { to: '/list', icon: ListIcon, label: 'List' },
  { to: '/plan', icon: Calendar, label: 'Plan' },
];

const BottomNav = () => (
  <nav
    aria-label="Primary"
    className="fixed inset-x-0 bottom-0 z-toast lg:hidden bg-white border-t border-slate-200 pb-[env(safe-area-inset-bottom)]"
  >
    <div className="flex items-stretch justify-around h-14">
      {TABS.map((tab) => {
        const Icon = tab.icon;
        return (
          <NavLink
            key={tab.to}
            to={tab.to}
            end={tab.to === '/map'}
            className={({ isActive }) =>
              [
                'flex flex-col items-center justify-center gap-0.5 flex-1 min-h-touch min-w-touch',
                'text-xs transition-colors',
                isActive
                  ? 'text-primary-600 font-medium'
                  : 'text-slate-500 hover:text-slate-700',
              ].join(' ')
            }
          >
            {({ isActive }) => (
              <>
                <Icon className="w-5 h-5" aria-hidden="true" />
                <span aria-current={isActive ? 'page' : undefined}>{tab.label}</span>
              </>
            )}
          </NavLink>
        );
      })}
    </div>
  </nav>
);

export default BottomNav;
