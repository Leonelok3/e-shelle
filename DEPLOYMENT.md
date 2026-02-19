# Immigration97 Home Page Deployment Guide

## Overview
This guide covers the **premium 2026 SAAS home page** enhancement with A/B theme variants, scroll animations, i18n support, and responsive mobile design.

**Completed Features:**
- ✅ Dark/Light theme toggle with localStorage persistence
- ✅ Scroll-triggered fade-in animations with stagger delays
- ✅ Multi-language support (French, English, Spanish)
- ✅ Animated stat counters (0 → target value)
- ✅ Mobile responsive (1024px, 768px, 480px breakpoints)
- ✅ Premium hero section with gradient text & animations
- ✅ Service card hover effects & polish

---

## Files Modified/Created

### Templates
- **`templates/home.html`** — Main landing page
  - Added `data-i18n-key` attributes for translation framework
  - Theme toggle button (top-right)
  - Script includes for animations & i18n

### Stylesheets
- **`static/css/home.css`** — ~1650 lines
  - Dark theme (default) with CSS custom properties
  - Light theme variant: `body.home[data-theme="light"]`
  - Responsive media queries: 1024px, 768px, 480px
  - Scroll animation keyframes: `@keyframes fadeInUp`

### JavaScript (New)
- **`static/js/theme-switch.js`**
  - Toggle dark ↔ light theme
  - Persists to localStorage[imm97_theme]
  - Updates `data-theme` attribute on body.home

- **`static/js/scroll-animations.js`**
  - IntersectionObserver for fade-in-up animations
  - Observes: `.service-card`, `.why-item`, `.section-header`, `.stat-item__value`
  - Stagger delays: 0ms, 120ms, 240ms, 360ms for grid children

- **`static/js/i18n-connector.js`**
  - Multi-language translations (fr, en, es)
  - Loads on page load via `loadTranslations()`
  - Global `changeLanguage(lang)` API for language switching

- **`static/js/counter-animate.js`**
  - Animate stat numbers from 0 → target on scroll
  - Uses RequestAnimationFrame for smooth animation
  - Formats French numbers with spaces (e.g., 12 000)

---

## Deployment Instructions

### 1. Pre-Deployment Checklist

```bash
# Run all tests (ensure no regressions)
python manage.py test core photos preparation_tests -v 2

# Check for syntax errors in static files
python manage.py collectstatic --dry-run --noinput

# Verify database migrations
python manage.py migrate --plan
```

**Expected Result:** 
- All tests pass (core, photos, preparation_tests)
- No collectstatic errors
- Migrations show "OK" status

### 2. Static Files Collection (Production)

```bash
# Collect all static files to STATIC_ROOT
python manage.py collectstatic --noinput --clear

# Verify CSS & JS are copied
ls -la staticfiles/css/home.css
ls -la staticfiles/js/{theme-switch,scroll-animations,i18n-connector,counter-animate}.js
```

### 3. Database Migrations (if any)

```bash
# Apply all pending migrations
python manage.py migrate

# Verify home page loads without errors
curl https://your-domain.com/ | grep "home-hero"
```

### 4. Cache Invalidation (CDN/Browser)

If using CDN (CloudFlare, AWS CloudFront):
```bash
# Invalidate CSS & JS cache
# Example: CloudFlare API
curl -X POST "https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache" \
  -H "Authorization: Bearer {api_token}" \
  -d '{"files": [
    "https://your-domain.com/static/css/home.css",
    "https://your-domain.com/static/js/theme-switch.js",
    "https://your-domain.com/static/js/scroll-animations.js",
    "https://your-domain.com/static/js/i18n-connector.js",
    "https://your-domain.com/static/js/counter-animate.js"
  ]}'
```

For browser cache, add version query params:
```html
<link rel="stylesheet" href="{% static 'css/home.css' %}?v=2024-01">
<script src="{% static 'js/theme-switch.js' %}?v=2024-01" defer></script>
```

---

## A/B Theme Testing

### Manual Testing (Local)

1. **Dark Theme (Default)**
   ```bash
   python manage.py runserver
   # Visit http://localhost:8000
   # Page loads with dark background, light text
   ```

2. **Light Theme Toggle**
   ```bash
   # Click "Theme: Dark" button (top-right corner)
   # Page switches to light background, dark text
   # localStorage[imm97_theme] = "light" (persists on reload)
   ```

3. **Verify LocalStorage Persistence**
   ```javascript
   // Browser DevTools Console
   localStorage.getItem('imm97_theme')  // Should return "light" or undefined
   localStorage.removeItem('imm97_theme')  // Reset to dark
   ```

### A/B Testing (Production)

**Option 1: Via URL Parameter**
Add to `config/urls.py`:
```python
from django.http import HttpResponse
from django.conf import settings

def home_view_light(request):
    response = render(request, 'home.html')
    response.set_cookie('imm97_theme_override', 'light', max_age=86400)  # 24h
    return response

urlpatterns = [
    path('', views.home, name='home'),
    path('home-light/', home_view_light, name='home_light'),  # A/B test variant
]
```

**Option 2: Via Analytics Tag**
In `templates/home.html`:
```html
<script>
  // Log theme variant to analytics
  const currentTheme = localStorage.getItem('imm97_theme') || 'dark';
  gtag('config', 'GA_MEASUREMENT_ID', {
    'custom_map': {
      'dimension1': 'theme_variant'
    }
  });
  gtag('event', 'page_view', {
    'theme_variant': currentTheme
  });
</script>
```

---

## i18n (Internationalization) Setup

### Current Translation Keys

```javascript
// Translatable elements in home.html
data-i18n-key="hero_title"       // Main headline
data-i18n-key="hero_subtitle"    // Subheading
data-i18n-key="hero_lead"        // Paragraph
```

### Supported Languages
- **fr** (French) — Default
- **en** (English)
- **es** (Spanish)

### Adding New Translations

**1. Edit `static/js/i18n-connector.js`:**
```javascript
const translations = {
  hero_title: {
    fr: "Ton projet d'immigration légale...",
    en: "Your legal immigration project...",
    es: "Tu proyecto de inmigración legal...",
  },
  // ADD NEW KEYS HERE
  new_feature: {
    fr: "Nouvelle fonctionnalité",
    en: "New feature",
    es: "Nueva característica",
  }
};
```

**2. Add `data-i18n-key` to HTML:**
```html
<h2 data-i18n-key="new_feature">Nouvelle fonctionnalité</h2>
```

**3. Test Translation:**
```javascript
// Browser Console
changeLanguage('en')   // Switch to English
changeLanguage('es')   // Switch to Spanish
changeLanguage('fr')   // Switch back to French
```

### Dynamic Language Switching (Optional)

Add language selector to navbar:
```html
<select id="language-selector" onchange="changeLanguage(this.value)">
  <option value="fr">Français</option>
  <option value="en">English</option>
  <option value="es">Español</option>
</select>

<script>
  document.getElementById('language-selector').addEventListener('change', (e) => {
    changeLanguage(e.target.value);
    localStorage.setItem('imm97_lang', e.target.value);
  });
  
  // Restore saved language on load
  const savedLang = localStorage.getItem('imm97_lang') || 'fr';
  document.getElementById('language-selector').value = savedLang;
  changeLanguage(savedLang);
</script>
```

---

## Responsive Design Testing

### Breakpoints

| Breakpoint | Device | CSS Media Query |
|-----------|--------|-----------------|
| 1024px | Tablet | `@media (max-width: 1024px)` |
| 768px | iPad/Mobile | `@media (max-width: 768px)` |
| 480px | Small Phone | `@media (max-width: 480px)` |

### Manual Testing

1. **Desktop (1920px+)**
   ```bash
   python manage.py runserver
   firefox http://localhost:8000 --width 1920 --height 1080
   # Verify: Full-width layout, 3-column service cards
   ```

2. **Tablet (768-1024px)**
   ```bash
   # Chrome DevTools: Toggle Device Toolbar → iPad
   # Verify: 2-column service cards, optimized padding
   ```

3. **Mobile (480-768px)**
   ```bash
   # Chrome DevTools: iPhone 12
   # Verify: Single-column layout, stacked buttons, readable text
   ```

4. **Small Phone (< 480px)**
   ```bash
   # Chrome DevTools: iPhone SE
   # Verify: Extra-small font sizes, minimal padding, hero stacked CTA
   ```

---

## Performance Optimization

### Lazy Loading (Optional)

If home page becomes heavy with images:
```html
<!-- In templates/home.html -->
<img src="..." alt="..." loading="lazy">
```

### CSS Critical Path (Optional)

Extract critical CSS above-the-fold:
```html
<style>
  /* Critical CSS for hero section only */
  body.home .home-hero { ... }
  body.home .home-hero__title { ... }
</style>
```

### JavaScript Deferral (Already Implemented)

All scripts load with `defer`:
```html
<script src="..." defer></script>
```
This ensures HTML parsing isn't blocked.

---

## Troubleshooting

### Theme Toggle Not Working

**Issue:** Light theme button click doesn't change theme.

**Solution:**
```bash
# Check browser console for errors
# Verify localStorage is enabled: Devtools → Application → Local Storage
# Check theme-switch.js is loaded: Devtools → Network tab

# If file not found:
python manage.py collectstatic --noinput
```

### Animations Not Triggering

**Issue:** Service cards don't fade in on scroll.

**Solution:**
```javascript
// Browser Console
// Check if scroll-animations.js loaded
console.log(typeof IntersectionObserver)  // Should be "function"

// Check if observer is watching elements
document.querySelectorAll('.service-card')  // Should return card elements
```

### i18n Not Translating

**Issue:** Changing language doesn't update text.

**Solution:**
```javascript
// Browser Console
console.log(translations.hero_title)  // Check if translations exist
changeLanguage('en')  // Force language change
```

---

## Rollback Plan

If deployment fails:

```bash
# 1. Identify last working version
git log --oneline | head -5

# 2. Revert to previous commit
git revert HEAD
# OR
git reset --hard HEAD~1

# 3. Re-collect static files
python manage.py collectstatic --noinput --clear

# 4. Restart application
sudo systemctl restart immigration97  # Or your app service
```

---

## Monitoring (Post-Deployment)

### Core Metrics to Track

1. **Page Load Time**
   - Goal: < 2 seconds
   - Tool: Google Analytics → Page Speed Insights

2. **Theme Toggle Usage**
   ```javascript
   // Add event tracking
   gtag('event', 'theme_toggle', {
     'from_theme': oldTheme,
     'to_theme': newTheme
   });
   ```

3. **Mobile Traffic**
   - Monitor bounce rate on mobile versions
   - Goal: < 70% bounce rate

4. **Error Tracking**
   - Set up Sentry or similar for JS errors
   - Monitor console errors in production

---

## Next Steps

1. ✅ **Done:** Deploy home page with themes & animations
2. **TODO:** Add language selector to navbar
3. **TODO:** Integrate Sentry for error tracking
4. **TODO:** Set up A/B testing via Google Analytics
5. **TODO:** Create landing page for premium upsell

---

## Support & Questions

For issues or feature requests:
- Check `DEPLOYMENT.md` troubleshooting section
- Review browser console errors (F12 → Console)
- Test locally: `python manage.py runserver`
- Run tests: `python manage.py test core photos`

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2024.01 | Jan 2024 | Initial premium home page release (themes, animations, i18n, responsive) |

