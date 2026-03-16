        // Debug mode - can be enabled via URL parameter ?debug=true
        let debugMode = false;
        
        // How often to check for updates (in milliseconds)
        const refreshInterval = 3000;
        
        // API endpoint
        const apiEndpoint = '/nowplaying';
        
        // Keep track of previous state
        let previousState = null;
        let containerVisible = true;
        let errorCount = 0;
        
        // Parse URL parameters
        function getUrlParams() {
            const params = {};
            const queryString = window.location.search;
            const urlParamsObj = new URLSearchParams(queryString);
            
            // Check for debug parameter
            if (urlParamsObj.has('debug') && urlParamsObj.get('debug') === 'true') {
                debugMode = true;
                console.log("Debug mode enabled");
            }
            
            // Get scene parameter
            const scene = urlParamsObj.get('scene');
            if (scene) {
                params.scene = scene;
            }
            
            return params;
        }
        
        // Get URL parameters
        const urlParams = getUrlParams();
        const currentScene = urlParams.scene || 'default';
        
        // Get scene-specific setting from localStorage with fallback
        function getSceneStorage(key, defaultValue) {
            // Try to get scene-specific setting first
            const sceneSpecific = localStorage.getItem(`${currentScene}_${key}`);
            if (sceneSpecific !== null) {
                return sceneSpecific;
            }
            
            // Fall back to global setting if available
            const global = localStorage.getItem(key);
            if (global !== null) {
                return global;
            }
            
            // Use default value if nothing is stored
            return defaultValue;
        }
        
        // Save setting with scene-specific storage
        function setSceneStorage(key, value) {
            localStorage.setItem(`${currentScene}_${key}`, value);
        }
        
        // Theme selection
        const themeButtons = document.querySelectorAll('.theme-btn[data-theme]');
        const widthButtons = document.querySelectorAll('.width-toggle');
        const container = document.querySelector('.overlay-container');
        
        // Migration: Copy global settings to default scene if needed
        if (currentScene === 'default' && localStorage.getItem('musicPlayerTheme') !== null && 
            localStorage.getItem('default_musicPlayerTheme') === null) {
            
            // Migrate theme setting
            if (localStorage.getItem('musicPlayerTheme')) {
                let oldTheme = localStorage.getItem('musicPlayerTheme');
                // Migrate old polar theme name to natural
                if (oldTheme === 'polar') {
                    oldTheme = 'natural';
                }
                localStorage.setItem('default_musicPlayerTheme', oldTheme);
            }
            
            // Migrate width setting
            if (localStorage.getItem('musicPlayerWidth')) {
                localStorage.setItem('default_musicPlayerWidth', localStorage.getItem('musicPlayerWidth'));
            }
        }
        
        // Get saved theme or use default
        const savedTheme = getSceneStorage('musicPlayerTheme', 'natural');
        document.body.className = `theme-${savedTheme}`;
        
        // Get saved width setting or use default (now 'fixed')
        const savedWidth = getSceneStorage('musicPlayerWidth', 'fixed');
        if (savedWidth === 'fixed') {
            container.classList.remove('width-adaptive');
            container.classList.add('width-fixed');
        } else {
            container.classList.add('width-adaptive');
            container.classList.remove('width-fixed');
        }
        
        // Update active button states
        themeButtons.forEach(btn => {
            if (btn.dataset.theme === savedTheme) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
        
        widthButtons.forEach(btn => {
            if (btn.dataset.width === savedWidth) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
        
        // Add click handlers for theme buttons
        themeButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const theme = btn.dataset.theme;
                
                // Update body class
                document.body.className = `theme-${theme}`;
                
                // Update active state
                themeButtons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                // Save selection with scene context
                setSceneStorage('musicPlayerTheme', theme);
                
                // Re-check if scrolling is needed after theme change.
                requestAnimationFrame(() => { 
                    songTitleMarquee._checkNeedsScroll(); 
                    songArtistMarquee._checkNeedsScroll();
                });
            });
        });
        
        // Add click handlers for width toggle
        widthButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const width = btn.dataset.width;
                
                // Update container class
                if (width === 'fixed') {
                    container.classList.remove('width-adaptive');
                    container.classList.add('width-fixed');
                } else {
                    container.classList.add('width-adaptive');
                    container.classList.remove('width-fixed');
                }
                
                // Update active state
                widthButtons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                // Save selection with scene context
                setSceneStorage('musicPlayerWidth', width);
                
                // Re-check if scrolling is needed after width change.
                 requestAnimationFrame(() => { 
                    songTitleMarquee._checkNeedsScroll();
                    songArtistMarquee._checkNeedsScroll();
                });
            });
        });

        // --- New Marquee Controller Logic ---
        class MarqueeController {
            // textElementId now refers to the ID of the inner span
            constructor(textElementId) { 
                this.innerElement = document.getElementById(textElementId); // Reference to the inner span
                this.outerElement = this.innerElement.parentElement; // Reference to the outer .scroll-text
                this.container = this.outerElement.parentElement; // Reference to .scroll-container
                this.originalText = '';
                this.needsScroll = false;
                this.animationFrameRequest = null;
            }

            _measureWidths() {
                // Get the container width
                const containerWidth = this.container.clientWidth;
                
                // Create a temporary span for accurate text measurement
                const tempSpan = document.createElement('span');
                
                // Copy all styles that could affect text rendering
                const computedStyle = window.getComputedStyle(this.innerElement);
                tempSpan.style.fontFamily = computedStyle.fontFamily;
                tempSpan.style.fontSize = computedStyle.fontSize;
                tempSpan.style.fontWeight = computedStyle.fontWeight;
                tempSpan.style.letterSpacing = computedStyle.letterSpacing;
                tempSpan.style.textTransform = computedStyle.textTransform;
                tempSpan.style.whiteSpace = 'nowrap';
                tempSpan.style.display = 'inline-block';
                tempSpan.style.position = 'absolute';
                tempSpan.style.visibility = 'hidden';
                tempSpan.textContent = this.originalText;
                
                // Add to document, measure, and remove
                document.body.appendChild(tempSpan);
                const textWidth = tempSpan.getBoundingClientRect().width;
                document.body.removeChild(tempSpan);
                
                // Only log measurements in debug mode
                if (debugMode) {
                    console.log(`[${this.innerElement.id}] Text: "${this.originalText}", Width: ${textWidth}px, Container: ${containerWidth}px`);
                }
                
                return { textWidth, containerWidth };
            }

            _checkNeedsScroll() { // Removed triggerInitialScroll parameter
                // Clear any pending animation frame requests for measurement
                cancelAnimationFrame(this.animationFrameRequest);
                
                // Reset visual state before measurement
                this.innerElement.classList.remove('scrolling-active'); // Remove class if present
                // The line setting style.animation = 'none' was removed as it conflicts with the class-based animation.
                this.innerElement.style.transform = 'translateX(0)'; // Ensure reset
                
                // Set text content on inner span to original for measurement consistency
                this.innerElement.textContent = this.originalText;

                // Use rAF to ensure DOM is updated before measuring
                this.animationFrameRequest = requestAnimationFrame(() => {
                    // Perform measurement using the clean original text state
                    const { textWidth, containerWidth } = this._measureWidths();
                    // Add a tolerance (e.g., 1 pixel) to prevent scrolling for tiny overflows
                    const scrollTolerance = 1; 
                    this.needsScroll = textWidth > (containerWidth + scrollTolerance);

                    // Now, update inner span's text content and apply/remove class based on whether scroll is needed
                    if (this.needsScroll) {
                        if (debugMode) console.log(`[${this.innerElement.id}] Needs scroll. Applying CSS animation.`);
                        
                        // Calculate the EXACT distance needed to show the full text
                        // If text is 400px and container is 200px, we need to scroll -200px
                        // Add 5px buffer to ensure the last character is fully visible
                        const scrollDistance = -(textWidth - containerWidth + 5);
                        
                        // --- New Duration Calculation for Consistent Speed ---
                        let calculatedDuration = 23; // Default duration if no scroll needed or minimal overflow
                        const minDuration = 15; // Minimum loop time to prevent extreme speed
                        const maxDuration = 60; // Maximum loop time
                        const scrollSpeed = 50; // Target pixels per second during scroll phase

                        if (textWidth > containerWidth) {
                            const scrollAmount = textWidth - containerWidth;
                            
                            // Calculate time needed for one-way scroll at target speed
                            const oneWayScrollTime = scrollAmount / scrollSpeed;

                            // The CSS keyframes allocate 15% of the total duration for the scroll-out phase (15% to 30%)
                            // So, oneWayScrollTime = 0.15 * totalDuration
                            // Therefore, totalDuration = oneWayScrollTime / 0.15
                            calculatedDuration = oneWayScrollTime / 0.15;

                            // Add buffer for very short scrolls to prevent them being too fast overall
                            // If scroll amount is small, the calculated duration might be very short.
                            // Let's ensure a minimum reasonable loop time.
                            calculatedDuration = Math.max(minDuration, calculatedDuration);
                            
                            // Cap the duration to prevent excessively long loops for huge text
                            calculatedDuration = Math.min(maxDuration, calculatedDuration);

                            if (debugMode) console.log(`[${this.innerElement.id}] Scroll Amount: ${scrollAmount.toFixed(1)}px, OneWayTime: ${oneWayScrollTime.toFixed(1)}s, Calculated Duration: ${calculatedDuration.toFixed(1)}s`);
                        } else {
                             if (debugMode) console.log(`[${this.innerElement.id}] No scroll needed, using default duration.`);
                        }

                        // Set custom property for animation duration with error checking
                        try {
                            // Use the newly calculated duration
                            this.innerElement.style.setProperty('--scroll-duration', `${calculatedDuration}s`);

                            // Set the custom property for scroll distance (still needed by keyframes)
                            this.innerElement.style.setProperty('--scroll-distance', `${scrollDistance}px`);
                            
                            // Debug check if custom properties are supported
                            if (debugMode) {
                                // Check if custom property was actually set
                                const computed = window.getComputedStyle(this.innerElement);
                                const durationValue = computed.getPropertyValue('--scroll-duration');
                                const distanceValue = computed.getPropertyValue('--scroll-distance');
                                
                                console.log(`[DEBUG] Custom properties set:
                                  --scroll-duration: ${durationValue || 'NOT SET'}
                                  --scroll-distance: ${distanceValue || 'NOT SET'}`);
                                
                                if (!durationValue || !distanceValue) {
                                    console.warn("CSS custom properties aren't working correctly!");
                                    showDebugError("CSS custom properties not working", 
                                      "This could be why marquee animation isn't working correctly in compiled app");
                                }
                            }
                        } catch (e) {
                            console.error("Error setting CSS properties:", e);
                            // Fallback to inline styles if custom properties fail
                            this.innerElement.style.animationDuration = `${calculatedDuration}s`;
                        }

                        // Add animation class
                        this.innerElement.classList.add('scrolling-active');
                    } else {
                        if (debugMode) console.log(`[${this.innerElement.id}] No scroll needed.`);
                        // Ensure original text is displayed on inner span if no scroll needed
                        this.innerElement.textContent = this.originalText;
                        // Ensure animation class is removed
                        this.innerElement.classList.remove('scrolling-active');
                    }
                });
            }

            updateText(newText) {
                const textChanged = newText !== this.originalText;
                
                // Stop any ongoing scroll/timers before updating
                this.stop(); // Ensures animation class is removed from inner span and text reset
                
                this.originalText = newText || ''; // Handle null/undefined
                this.innerElement.textContent = this.originalText; // Set initial text on inner span
                
                if (this.originalText) {
                    // Check if scroll is needed and apply/remove class to inner span
                    this._checkNeedsScroll(); 
                } else {
                    // No text, ensure needsScroll is false and inner element is empty
                    this.needsScroll = false; 
                    this.innerElement.textContent = '';
                    this.innerElement.classList.remove('scrolling-active'); // Ensure class is removed from inner span
                }
            }

            stop() {
                if (debugMode) console.log(`[${this.innerElement.id}] Stopping marquee.`);
                // Cancel pending measurement checks
                cancelAnimationFrame(this.animationFrameRequest);
                
                // Reset visual state by removing animation class
                this.innerElement.classList.remove('scrolling-active');
                // Ensure transform is reset (base style should handle this)
                this.innerElement.style.transform = 'translateX(0)'; 
                // Remove custom properties
                this.innerElement.style.removeProperty('--scroll-distance');
                this.innerElement.style.removeProperty('--scroll-duration');
                
                // Reset text content on inner span to the base original text
                this.innerElement.textContent = this.originalText; 
            }
            
            clear() {
                if (debugMode) console.log(`[${this.innerElement.id}] Clearing marquee.`);
                this.stop();
                this.originalText = '';
                this.innerElement.textContent = ''; // Clear text on inner span
            }
        }

        // Instantiate controllers for title and artist
        const songTitleMarquee = new MarqueeController('songTitle');
        const songArtistMarquee = new MarqueeController('songArtist');
        // --- End Marquee Controller Logic ---
        
        // Function to show debug error
        function showDebugError(message, error) {
            if (debugMode) {
                const errorContainer = document.getElementById('errorContainer');
                const errorText = document.getElementById('errorText');
                
                errorContainer.style.display = 'block';
                errorText.textContent = `Error: ${message}\n${error ? error.toString() : ''}`;
                
                // Log to console as well
                console.error(message, error);
            }
        }

        
        // Function to fetch and display song info
        function updateNowPlaying() {
            fetch(apiEndpoint + '?t=' + new Date().getTime(), {
                method: 'GET',
                headers: {
                    'Accept': 'application/json'
                }
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Server returned ${response.status} ${response.statusText}`);
                }
                return response.text();
            })
            .then(text => {
                // Make sure we have some content
                if (!text || text.trim() === '') {
                    throw new Error('Empty response from server');
                }

                // Add logging for raw text in debug mode
                if (debugMode) {
                    console.log("[Debug] Raw response text:", text);
                }
                
                // Try to parse as JSON
                try {
                    const data = JSON.parse(text);
                    errorCount = 0; // Reset error count on success

                    // Add logging for parsed data and previous state in debug mode
                    if (debugMode) {
                        console.log("[Debug] Parsed data:", JSON.stringify(data));
                        console.log("[Debug] Previous state:", JSON.stringify(previousState));
                    }
                    
                    // Only update the UI if the data has changed
                    if (JSON.stringify(data) !== JSON.stringify(previousState)) {
                        const container = document.getElementById('musicContainer');
                        
                        if (data.playing) {
                            // Show container if hidden
                            if (!containerVisible) {
                                container.classList.remove('hidden');
                                containerVisible = true;
                            }
                            
                            // Animate if song changed
                            if (!previousState || previousState.title !== data.title) {
                                container.style.animation = 'none';
                                container.offsetHeight; // Trigger reflow
                                container.style.animation = 'fadeIn 0.5s ease-in-out';
                            }
                            
                            const songTitleEl = document.getElementById('songTitle');
                            const songArtistEl = document.getElementById('songArtist');
                            
                            const titleText = data.title;
                            const artistAlbumText = data.artist + (data.album ? ` • ${data.album}` : '');
                            
                            songTitleEl.classList.remove('not-playing');
                            
                            // Update text using Marquee Controllers ONLY if text changed
                            if (!previousState || titleText !== previousState.title) {
                                if (debugMode) console.log(`[Main] Title changed: "${previousState?.title}" -> "${titleText}"`);
                                songTitleMarquee.updateText(titleText);
                            }
                            
                            const prevArtistAlbumText = (previousState?.artist || '') + (previousState?.album ? ` • ${previousState.album}` : '');
                            if (!previousState || artistAlbumText !== prevArtistAlbumText) {
                                if (debugMode) console.log(`[Main] Artist/Album changed: "${prevArtistAlbumText}" -> "${artistAlbumText}"`);
                                songArtistMarquee.updateText(artistAlbumText);
                            }
                            
                            // Update artwork
                            const artworkContainer = document.getElementById('artworkContainer');
                            const songChanged = !previousState || previousState.title !== data.title;
                            
                            if (data.artworkPath) {
                                // Update artwork if the path changed OR if the song changed.
                                // Checking song title as well guards against cases where a
                                // queued track's art temporarily lands on disk with the same
                                // mtime-based URL, which would otherwise get stuck showing
                                // the wrong album art for the current track.
                                if (songChanged || previousState.artworkPath !== data.artworkPath) {
                                    // Preload the new image first
                                    const newImg = new Image();
                                    newImg.onload = function() {
                                        artworkContainer.innerHTML = `<img src="${data.artworkPath}" alt="Album art">`;
                                        artworkContainer.className = 'album-art';
                                    };
                                    // Force a cache-busting reload when the song changes so the
                                    // browser doesn't serve a cached copy of the old artwork.
                                    newImg.src = songChanged
                                        ? data.artworkPath + '&song=' + encodeURIComponent(data.title)
                                        : data.artworkPath;
                                }
                            } else {
                                // No artwork, show music note
                                artworkContainer.innerHTML = '♪';
                                artworkContainer.className = 'note-icon';
                            }
                            
                            
                        } else {
                            // Stop marquees and clear text if not playing or error
                            songTitleMarquee.clear(); // Clear text and stop animation
                            songArtistMarquee.clear(); // Clear text and stop animation

                            // Check the specific error message
                            if (data.error === "Music app not running") {
                                // If Music app isn't running, hide the container completely
                                if (containerVisible) {
                                    container.classList.add('hidden');
                                    containerVisible = false;
                                    if (debugMode) console.log("[Main] Music app not running, hiding container.");
                                }
                                // Ensure text is cleared (already done by .clear() above)
                            } else if (data.error) {
                                // For other errors, show "Music information unavailable"
                                if (!containerVisible) { // Ensure container is visible for error message
                                    container.classList.remove('hidden');
                                    containerVisible = true;
                                }
                                songTitleMarquee.updateText("Music information unavailable"); 
                                document.getElementById('songTitle').classList.add('not-playing');
                                // Artist marquee already cleared by .clear() above
                                
                                if (debugMode) {
                                    showDebugError(`Server reports issue: ${data.error}`);
                                }
                            } else {
                                // If simply not playing (no error), hide the container
                                if (containerVisible) {
                                    container.classList.add('hidden');
                                    containerVisible = false;
                                    if (debugMode) console.log("[Main] Music not playing (no error), hiding container.");
                                }
                            }
                        }
                        
                        previousState = data;
                    }
                    
                    // Hide any error messages
                    if (!debugMode) {
                        document.getElementById('errorContainer').style.display = 'none';
                    }
                } catch (parseError) {
                    showDebugError('JSON parsing error', parseError);
                    throw parseError;
                }
            })
            .catch(error => {
                errorCount++;
                
                if (errorCount > 3) {
                    // Stop marquees and show connection error
                    songTitleMarquee.updateText("Connection error");
                    songArtistMarquee.clear(); // Clear artist line
                    document.getElementById('songTitle').classList.add('not-playing');
                    
                    showDebugError('Error fetching now playing info', error);
                }
            });
        }
        
        // If in debug mode, show the current scene in console
        if (debugMode) {
            console.log(`Current scene: ${currentScene}`);
            console.log(`Theme for this scene: ${savedTheme}`);
            console.log(`Width for this scene: ${savedWidth}`);
        }
        
        // Update immediately and then at regular intervals
        updateNowPlaying();
        setInterval(updateNowPlaying, refreshInterval);
