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
        this.currentVenue = 'catscradle';
        this.init();
    }

    async init() {
        this.setupVenueButtons();
        await this.loadVenue(this.currentVenue);
    }

    setupVenueButtons() {
        document.querySelectorAll('.venue-btn').forEach(btn => {
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
        document.querySelectorAll('.venue-btn').forEach(btn => {
            const isActive = btn.dataset.venue === venue;
            btn.classList.toggle('active', isActive);
            btn.setAttribute('aria-pressed', isActive);
        });

        this.currentVenue = venue;
        this.activePlayer = null;
        trackEvent('venue_switch', { venue_name: venue });
        await this.loadVenue(venue);
        document.getElementById('stats').scrollIntoView({ behavior: 'smooth' });
    }

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

    renderStats() {
        const stats = document.getElementById('stats');
        if (!this.data) return;

        const total = this.data.total_shows || 0;
        const withVideo = this.data.shows_with_video || 0;
        const venueName = this.data.venue?.name || '';

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
        const venueNames = {
            'catscradle': "Cat's Cradle",
            'local506': 'Local 506',
            'motorco': 'Motorco Music Hall',
            'kings': 'Kings',
            'mohawk': 'Mohawk Austin',
            'elevation27': 'Elevation 27',
            'pinhook': 'The Pinhook',
            'lincoln': 'Lincoln Theatre',
            'thesocial': 'The Social',
            'boweryballroom': 'Bowery Ballroom',
            'elclub': 'El Club'
        };
        const name = venueNames[venue] || venue;

        document.getElementById('shows-grid').innerHTML = `
            <div class="loading">
                <p>No shows data found for ${name}.</p>
                <p>Coming soon!</p>
            </div>
        `;
        document.getElementById('stats').innerHTML = '';
    }

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
