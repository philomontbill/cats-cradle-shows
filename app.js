// Soundcheck - Multi-Venue Show Discovery App

// GA4 event helper — safe to call even if gtag isn't loaded
function trackEvent(eventName, params) {
    if (typeof gtag === 'function') {
        gtag('event', eventName, params);
    }
}

class ShowsApp {
    constructor() {
        this.data = null;
        this.activePlayer = null;
        this.currentVenue = null;
        this.venueConfig = null;       // Full venues.json data
        this.venueLookup = {};         // slug → { name, city, website }
        this.currentState = null;
        this.currentRegion = null;
        this.init();
    }

    async init() {
        try {
            await this.loadVenueConfig();
            this.buildStateDropdown();
            this.selectState(this.venueConfig.default_state);
        } catch (error) {
            document.getElementById('shows-grid').innerHTML = `
                <div class="loading"><p>Unable to load venue configuration.</p></div>
            `;
        }
    }

    async loadVenueConfig() {
        const response = await fetch('data/venues.json?t=' + Date.now());
        if (!response.ok) throw new Error('Venue config not found');
        this.venueConfig = await response.json();

        // Build flat lookup for slug → venue metadata
        this.venueLookup = {};
        for (const state of this.venueConfig.states) {
            for (const region of state.regions) {
                for (const venue of region.venues) {
                    this.venueLookup[venue.slug] = venue;
                }
            }
        }
    }

    getState(abbr) {
        return this.venueConfig.states.find(s => s.abbr === abbr);
    }

    getVenueName(slug) {
        return this.venueLookup[slug]?.name || slug;
    }

    // --- Navigation ---

    buildStateDropdown() {
        const select = document.getElementById('state-select');
        select.innerHTML = this.venueConfig.states
            .map(s => `<option value="${s.abbr}">${s.name}</option>`)
            .join('');

        select.addEventListener('change', () => {
            this.selectState(select.value);
            trackEvent('state_switch', { state: select.value });
        });
    }

    selectState(abbr) {
        const state = this.getState(abbr);
        if (!state) return;

        this.currentState = abbr;
        document.getElementById('state-select').value = abbr;

        const regionSelect = document.getElementById('region-select');

        regionSelect.innerHTML = state.regions
            .map(r => `<option value="${r.slug}">${r.name}</option>`)
            .join('');
        regionSelect.onchange = () => {
            const region = state.regions.find(r => r.slug === regionSelect.value);
            if (region) this.selectRegion(region);
        };
        this.selectRegion(state.regions[0]);
    }

    selectRegion(region) {
        this.currentRegion = region;

        // Update tagline
        document.getElementById('tagline').textContent = region.tagline;

        // Render venue buttons
        this.renderVenueButtons(region.venues);

        // Auto-select first venue if current venue isn't in this region
        const regionSlugs = region.venues.map(v => v.slug);
        if (!this.currentVenue || !regionSlugs.includes(this.currentVenue)) {
            this.switchVenue(region.venues[0].slug);
        }
    }

    renderVenueButtons(venues) {
        const nav = document.getElementById('venue-buttons');
        nav.innerHTML = venues.map(v => {
            const isActive = v.slug === this.currentVenue;
            return `<button class="venue-btn${isActive ? ' active' : ''}" data-venue="${v.slug}" aria-pressed="${isActive}">${v.name}</button>`;
        }).join('');

        nav.querySelectorAll('.venue-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const venue = btn.dataset.venue;
                if (venue !== this.currentVenue) {
                    this.switchVenue(venue);
                }
            });
        });
    }

    async switchVenue(venue) {
        // Update button states
        document.querySelectorAll('#venue-buttons .venue-btn').forEach(btn => {
            const isActive = btn.dataset.venue === venue;
            btn.classList.toggle('active', isActive);
            btn.setAttribute('aria-pressed', isActive);
        });

        this.currentVenue = venue;
        this.activePlayer = null;
        trackEvent('venue_switch', { venue_name: this.getVenueName(venue) });
        await this.loadVenue(venue);
        document.getElementById('stats').scrollIntoView({ behavior: 'smooth' });
    }

    // --- Data Loading ---

    async loadVenue(venue) {
        try {
            await this.loadData(venue);
            this.renderStats();
            this.renderShows();
        } catch (error) {
            this.showError(venue);
        }
    }

    async loadData(venue) {
        const filename = `data/shows-${venue}.json`;
        const response = await fetch(`${filename}?t=${Date.now()}`);
        if (!response.ok) {
            throw new Error('Data not found');
        }
        this.data = await response.json();
    }

    // --- Rendering ---

    renderStats() {
        const stats = document.getElementById('stats');
        if (!this.data) return;

        const total = this.data.total_shows || 0;
        const withVideo = this.data.shows_with_video || 0;
        const venueName = this.getVenueName(this.currentVenue);

        stats.innerHTML = `
            <strong>${total}</strong> upcoming shows at ${venueName} &bull;
            <strong>${withVideo}</strong> with instant preview
            <p class="click-hint">Click any artist to hear their music. Opening acts are in <span class="blue-text">Blue</span>.</p>
        `;
    }

    renderShows() {
        const container = document.getElementById('shows-grid');
        const shows = (this.data?.shows || []).filter(s => !s.expired);

        if (shows.length === 0) {
            this.showError(this.currentVenue);
            return;
        }

        container.innerHTML = shows.map((show, index) => this.createShowCard(show, index)).join('');

        // Add click/key handlers for headliners
        container.querySelectorAll('.show-header').forEach((header, index) => {
            const show = shows[index];
            const handleHeadliner = (e) => {
                if (e.target.classList.contains('opener-name') ||
                    e.target.classList.contains('ticket-btn')) return;
                if (show.youtube_id) {
                    trackEvent('sample_play', {
                        artist: show.artist,
                        venue_name: show.venue,
                        role: 'headliner'
                    });
                    this.togglePlayer(index, show.youtube_id, show.artist);
                } else {
                    this.showNoPreview(show.artist);
                }
            };
            header.addEventListener('click', handleHeadliner);
            header.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    handleHeadliner(e);
                }
            });
        });

        // Add click/key handlers for openers
        container.querySelectorAll('.opener-name.has-video').forEach((openerEl) => {
            const index = parseInt(openerEl.dataset.openerIndex);
            const show = shows[index];
            if (show.opener_youtube_id) {
                const handleOpener = (e) => {
                    e.stopPropagation();
                    trackEvent('sample_play', {
                        artist: show.opener,
                        venue_name: show.venue,
                        role: 'opener'
                    });
                    this.togglePlayer(index, show.opener_youtube_id, show.opener);
                };
                openerEl.addEventListener('click', handleOpener);
                openerEl.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        handleOpener(e);
                    }
                });
            }
        });
    }

    createShowCard(show, index) {
        const hasImage = !!show.image;

        const imageHtml = hasImage
            ? `<div class="show-image">
                   <img src="${this.escapeHtml(show.image)}" alt="${this.escapeHtml(show.artist)}" loading="lazy">
               </div>`
            : '';

        const noticeHtml = show.notice
            ? `<div class="show-notice">${this.escapeHtml(show.notice)}</div>`
            : '';

        const openerHtml = show.opener
            ? `<div class="opener">with <span class="opener-name ${show.opener_youtube_id ? 'has-video' : ''}" data-opener-index="${index}"${show.opener_youtube_id ? ` tabindex="0" role="button" aria-label="${this.escapeHtml(show.opener)} — play sample"` : ''}>${this.escapeHtml(show.opener)}${show.opener_youtube_id ? ' <span class="play-icon" aria-hidden="true">&#9658;</span>' : ''}</span></div>`
            : '';

        const timesHtml = (show.doors || show.showtime)
            ? `<div class="show-times">
                   ${show.doors ? `<span>Doors: ${this.escapeHtml(show.doors)}</span>` : ''}
                   ${show.showtime ? `<span>Show: ${this.escapeHtml(show.showtime)}</span>` : ''}
               </div>`
            : '';

        const ticketUrl = show.event_url || show.ticket_url || '#';

        return `
            <div class="show-card" data-index="${index}">
                <div class="show-header" tabindex="0" role="button" aria-label="${this.escapeHtml(show.artist)}${show.youtube_id ? ' — play sample' : ' — no preview available'}">
                    ${imageHtml}
                    <div class="show-info">
                        ${noticeHtml}
                        <div class="artist-name has-video">${this.escapeHtml(show.artist)} <span class="play-icon ${show.youtube_id ? '' : 'no-video'}" aria-hidden="true">&#9658;</span></div>
                        ${openerHtml}
                        <div class="show-meta">
                            <span>${this.escapeHtml(show.date)}</span>
                            ${timesHtml}
                        </div>
                    </div>
                    <div class="card-right">
                        <div class="venue-tag">${this.escapeHtml(show.venue)}</div>
                        <a href="${this.escapeHtml(ticketUrl)}" target="_blank" rel="noopener noreferrer" class="ticket-btn" aria-label="Get Tickets for ${this.escapeHtml(show.artist)} (opens in new tab)" onclick="event.stopPropagation(); trackEvent('ticket_click', { artist: '${this.escapeHtml(show.artist).replace(/'/g, "\\'")}', venue_name: '${this.escapeHtml(show.venue).replace(/'/g, "\\'")}', ticket_url: '${this.escapeHtml(ticketUrl).replace(/'/g, "\\'")}' })">Get Tickets</a>
                    </div>
                </div>
                <div class="player-container" id="player-${index}">
                    <div class="player-wrapper"></div>
                </div>
            </div>
        `;
    }

    // --- Player ---

    togglePlayer(index, videoId, artistName) {
        const container = document.getElementById(`player-${index}`);
        const wrapper = container.querySelector('.player-wrapper');

        // If this player is already active, close it
        if (this.activePlayer === index) {
            container.classList.remove('active');
            wrapper.innerHTML = '';
            this.activePlayer = null;
            return;
        }

        // Close any other active player
        if (this.activePlayer !== null) {
            const prevContainer = document.getElementById(`player-${this.activePlayer}`);
            if (prevContainer) {
                prevContainer.classList.remove('active');
                prevContainer.querySelector('.player-wrapper').innerHTML = '';
            }
        }

        // Open this player
        container.classList.add('active');
        wrapper.innerHTML = `
            <iframe
                src="https://www.youtube.com/embed/${videoId}?rel=0&autoplay=1"
                title="YouTube video player for ${this.escapeHtml(artistName || 'artist')}"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowfullscreen>
            </iframe>
        `;
        this.activePlayer = index;

        // Scroll the card into view
        const card = container.closest('.show-card');
        setTimeout(() => {
            card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }, 100);
    }

    // --- Dialogs ---

    showNoPreview(artist) {
        // Remove any existing popup
        const existing = document.querySelector('.no-preview-popup');
        if (existing) existing.remove();

        // Save the element that triggered the modal so we can return focus
        const previousFocus = document.activeElement;

        const popup = document.createElement('div');
        popup.className = 'no-preview-popup';
        popup.innerHTML = `
            <div class="no-preview-content" role="dialog" aria-modal="true" aria-label="No preview available for ${this.escapeHtml(artist)}">
                <p>No preview yet for <strong>${this.escapeHtml(artist)}</strong></p>
                <p>Are you the artist? <a href="mailto:info@localsoundcheck.com?subject=Preview link for ${encodeURIComponent(artist)}&body=YouTube link:">Send us your link</a></p>
                <button class="no-preview-close" aria-label="Close dialog">&times;</button>
            </div>
        `;
        document.body.appendChild(popup);

        const closeBtn = popup.querySelector('.no-preview-close');
        const emailLink = popup.querySelector('a');

        const closePopup = () => {
            popup.remove();
            if (previousFocus) previousFocus.focus();
        };

        // Close handlers
        closeBtn.addEventListener('click', closePopup);
        popup.addEventListener('click', (e) => {
            if (e.target === popup) closePopup();
        });

        // Escape key closes
        popup.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                closePopup();
            }
            // Focus trap — keep Tab inside the dialog
            if (e.key === 'Tab') {
                const focusable = [emailLink, closeBtn];
                const first = focusable[0];
                const last = focusable[focusable.length - 1];
                if (e.shiftKey) {
                    if (document.activeElement === first) {
                        e.preventDefault();
                        last.focus();
                    }
                } else {
                    if (document.activeElement === last) {
                        e.preventDefault();
                        first.focus();
                    }
                }
            }
        });

        // Move focus into the dialog
        closeBtn.focus();
    }

    showError(venue) {
        const name = this.getVenueName(venue);
        document.getElementById('shows-grid').innerHTML = `
            <div class="loading">
                <p>No shows data found for ${name}.</p>
                <p>Coming soon!</p>
            </div>
        `;
        document.getElementById('stats').innerHTML = '';
    }

    // --- Utilities ---

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    new ShowsApp();
});
