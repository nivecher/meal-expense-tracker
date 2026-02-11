/**
 * Collapsible left sidebar behavior.
 */

const SIDEBAR_STORAGE_KEY = 'sidebarCollapsed';
const MOBILE_QUERY = '(max-width: 576px)';

function getSidebarShell() {
  return document.querySelector('.app-shell');
}

function isMobileViewport() {
  return window.matchMedia(MOBILE_QUERY).matches;
}

function applyDesktopCollapsedState(isCollapsed) {
  const shell = getSidebarShell();
  if (!shell) return;
  shell.classList.toggle('sidebar-collapsed', isCollapsed);
}

function setMobileSidebarOpen(isOpen) {
  const shell = getSidebarShell();
  if (!shell) return;
  shell.classList.toggle('sidebar-mobile-open', isOpen);
  document.body.classList.toggle('sidebar-mobile-open', isOpen);

  const icon = document.querySelector('[data-sidebar-mobile-icon]');
  if (icon instanceof HTMLElement) {
    icon.classList.toggle('fa-bars', !isOpen);
    icon.classList.toggle('fa-times', isOpen);
  }
}

function loadSidebarState() {
  try {
    return localStorage.getItem(SIDEBAR_STORAGE_KEY) === 'true';
  } catch {
    return false;
  }
}

function getInitialCollapsedState() {
  if (isMobileViewport()) return false;
  return loadSidebarState();
}

function saveSidebarState(isCollapsed) {
  try {
    localStorage.setItem(SIDEBAR_STORAGE_KEY, String(isCollapsed));
  } catch {
    // ignore
  }
}

function initSidebarToggle() {
  const toggleButton = document.querySelector('[data-sidebar-toggle]');
  const mobileToggleButtons = document.querySelectorAll('[data-sidebar-mobile-toggle]');
  const backdrop = document.querySelector('[data-sidebar-backdrop]');

  applyDesktopCollapsedState(getInitialCollapsedState());
  setMobileSidebarOpen(false);

  if (isMobileViewport()) {
    applyDesktopCollapsedState(false);
  }

  if (toggleButton) {
    toggleButton.addEventListener('click', () => {
      if (isMobileViewport()) {
        setMobileSidebarOpen(false);
        return;
      }
      const shell = getSidebarShell();
      if (!shell) return;
      const nextState = !shell.classList.contains('sidebar-collapsed');
      applyDesktopCollapsedState(nextState);
      saveSidebarState(nextState);
    });
  }

  const brandLink = document.querySelector('.sidebar-brand');
  if (brandLink) {
    brandLink.addEventListener('click', (event) => {
      if (isMobileViewport()) return;
      const shell = getSidebarShell();
      if (!shell || !shell.classList.contains('sidebar-collapsed')) return;
      event.preventDefault();
      applyDesktopCollapsedState(false);
      saveSidebarState(false);
    });
  }

  mobileToggleButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      const shell = getSidebarShell();
      if (!shell) return;
      const isOpen = shell.classList.contains('sidebar-mobile-open');
      setMobileSidebarOpen(!isOpen);
    });
  });

  if (backdrop) {
    backdrop.addEventListener('click', () => {
      setMobileSidebarOpen(false);
    });
  }

  const sidebar = document.querySelector('[data-sidebar]');
  if (sidebar) {
    sidebar.addEventListener('click', (event) => {
      if (!isMobileViewport()) return;
      const link = event.target.closest('a.sidebar-link, a.sidebar-sublink');
      if (link) {
        setMobileSidebarOpen(false);
      }
    });
  }

  document.addEventListener('keydown', (event) => {
    if (!isMobileViewport()) return;
    if (event.key === 'Escape') {
      setMobileSidebarOpen(false);
    }
  });

  window.addEventListener('resize', () => {
    const isMobile = isMobileViewport();
    setMobileSidebarOpen(false);
    if (isMobile) {
      applyDesktopCollapsedState(false);
      return;
    }
    applyDesktopCollapsedState(getInitialCollapsedState());
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initSidebarToggle();
});
