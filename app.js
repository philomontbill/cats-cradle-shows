// Cat's Cradle Show Discovery App
class ShowsApp {
    constructor() {
        this.data = null;
        this.activePlayer = null;
        this.init();
    }

    async init() {
        try {
            await this.loadData();
            this.renderStats();
            this.renderShows();
        } catch (error) {
            this.showError();
        }
    }

    async loadData() {
        const response = await fetch(`shows.json?t=${Date.now()}`);
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

        stats.innerHTML = `
            <strong>${total}</strong> upcoming shows &bull;
            <strong>${withVideo}</strong> with instant preview
        `;
    }

    renderShows() {
        const container = document.getElementById('shows-grid');
        const shows = this.data?.shows || [];

        if (shows.length === 0) {
            this.showError();
            return;
        }

        container.innerHTML = shows.map((show, index) => this.createShowCard(show, index)).join('');

        // Add click handlers for headliners
        container.querySelectorAll('.show-header').forEach((header, index) => {
            const show = shows[index];
            if (show.youtube_id) {
                header.addEventListener('click', (e) => {
                    // Don't trigger if clicking on opener
                    if (e.target.classList.contains('opener-name')) return;
                    this.togglePlayer(index, show.youtube_id);
                });
            }
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
        const hasVideo = !!show.youtube_id;
        const hasImage = !!show.image;

        const imageHtml = hasImage
            ? `<div class="show-image">
                   <img src="${this.escapeHtml(show.image)}" alt="${this.escapeHtml(show.artist)}" loading="lazy">
               </div>`
            : '';

        const openerHtml = show.opener
            ? `<div class="opener">with <span class="opener-name ${show.opener_youtube_id ? 'has-video' : ''}" data-opener-index="${index}">${this.escapeHtml(show.opener)}</span></div>`
            : '';

        const timesHtml = (show.doors || show.showtime)
            ? `<div class="show-times">
                   ${show.doors ? `<span>Doors: ${this.escapeHtml(show.doors)}</span>` : ''}
                   ${show.showtime ? `<span>Show: ${this.escapeHtml(show.showtime)}</span>` : ''}
               </div>`
            : '';

        return `
            <div class="show-card ${hasVideo ? 'has-video' : 'no-video'}" data-index="${index}">
                <div class="show-header">
                    ${imageHtml}
                    <div class="show-info">
                        <div class="artist-name">
                            ${this.escapeHtml(show.artist)}
                            <span class="play-icon">&#9658;</span>
                        </div>
                        ${openerHtml}
                        <div class="show-meta">
                            <span>${this.escapeHtml(show.date)}</span>
                            ${timesHtml}
                        </div>
                    </div>
                    <div class="venue-tag">${this.escapeHtml(show.venue)}</div>
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
                src="https://www.youtube.com/embed/${videoId}?autoplay=1&rel=0"
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

    showError() {
        document.getElementById('shows-grid').innerHTML = `
            <div class="loading">
                <p>No shows data found.</p>
                <p>Run <code>python scraper.py</code> to fetch shows.</p>
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
