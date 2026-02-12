// Soundcheck - Multi-Venue Show Discovery App
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
            btn.classList.toggle('active', btn.dataset.venue === venue);
        });

        this.currentVenue = venue;
        this.activePlayer = null;
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
        const filename = `shows-${venue}.json`;
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
        const shows = this.data?.shows || [];

        if (shows.length === 0) {
            this.showError(this.currentVenue);
            return;
        }

        container.innerHTML = shows.map((show, index) => this.createShowCard(show, index)).join('');

        // Add click handlers for headliners
        container.querySelectorAll('.show-header').forEach((header, index) => {
            const show = shows[index];
            header.addEventListener('click', (e) => {
                // Don't trigger if clicking on opener or ticket button
                if (e.target.classList.contains('opener-name') ||
                    e.target.classList.contains('ticket-btn')) return;
                if (show.youtube_id) {
                    this.togglePlayer(index, show.youtube_id);
                } else {
                    this.showNoPreview(show.artist);
                }
            });
        });

        // Add click handlers for openers
        container.querySelectorAll('.opener-name.has-video').forEach((openerEl) => {
            const index = parseInt(openerEl.dataset.openerIndex);
            const show = shows[index];
            if (show.opener_youtube_id) {
                openerEl.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.togglePlayer(index, show.opener_youtube_id);
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
            ? `<div class="opener">with <span class="opener-name ${show.opener_youtube_id ? 'has-video' : ''}" data-opener-index="${index}">${this.escapeHtml(show.opener)}${show.opener_youtube_id ? ' <span class="play-icon">&#9658;</span>' : ''}</span></div>`
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
                <div class="show-header">
                    ${imageHtml}
                    <div class="show-info">
                        ${noticeHtml}
                        <div class="artist-name has-video">${this.escapeHtml(show.artist)} <span class="play-icon ${show.youtube_id ? '' : 'no-video'}">&#9658;</span></div>
                        ${openerHtml}
                        <div class="show-meta">
                            <span>${this.escapeHtml(show.date)}</span>
                            ${timesHtml}
                        </div>
                    </div>
                    <div class="card-right">
                        <div class="venue-tag">${this.escapeHtml(show.venue)}</div>
                        <a href="${this.escapeHtml(ticketUrl)}" target="_blank" rel="noopener noreferrer" class="ticket-btn" onclick="event.stopPropagation()">Get Tickets</a>
                    </div>
                </div>
                <div class="player-container" id="player-${index}">
                    <div class="player-wrapper"></div>
                </div>
            </div>
        `;
    }

    togglePlayer(index, videoId) {
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
                src="https://www.youtube.com/embed/${videoId}?rel=0"
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

        const popup = document.createElement('div');
        popup.className = 'no-preview-popup';
        popup.innerHTML = `
            <div class="no-preview-content">
                <p>No preview yet for <strong>${this.escapeHtml(artist)}</strong></p>
                <p>Are you the artist? <a href="mailto:localsoundcheck@gmail.com?subject=Preview link for ${encodeURIComponent(artist)}&body=YouTube link:">Send us your link</a></p>
                <button class="no-preview-close">&times;</button>
            </div>
        `;
        document.body.appendChild(popup);

        popup.querySelector('.no-preview-close').addEventListener('click', () => popup.remove());
        popup.addEventListener('click', (e) => {
            if (e.target === popup) popup.remove();
        });
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
