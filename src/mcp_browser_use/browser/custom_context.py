# -*- coding: utf-8 -*-

import json
import logging
import os

from browser_use.browser.browser import Browser
from browser_use.browser.context import BrowserContext, BrowserContextConfig
from playwright.async_api import Browser as PlaywrightBrowser
from playwright.async_api import BrowserContext as PlaywrightBrowserContext

from mcp_browser_use.browser.config import BrowserPersistenceConfig

logger = logging.getLogger(__name__)


class CustomBrowserContext(BrowserContext):
    """
    A BrowserContext subclass that optionally reuses an existing Chrome context (if `chrome_instance_path`
    is set and a context is already present), or creates a new one. Allows for tracing, cookie loading,
    and injection of anti-detection scripts.
    """

    def __init__(
        self, browser: "Browser", config: BrowserContextConfig = BrowserContextConfig()
    ):
        super().__init__(browser=browser, config=config)

    async def _create_context(
        self, browser: PlaywrightBrowser
    ) -> PlaywrightBrowserContext:
        """
        Create or reuse a Playwright browser context with optional:
          - Cookie loading (if `cookies_file` is set)
          - Tracing (if `trace_path` is set)
          - Anti-detection scripts (disable certain detection features).

        :param browser: The PlaywrightBrowser instance to use.
        :return: A PlaywrightBrowserContext to be used by this CustomBrowserContext.
        """
        # If we have a custom Chrome instance and an existing context, reuse it
        if self.browser.config.chrome_instance_path and len(browser.contexts) > 0:
            logger.debug("Reusing the first existing browser context.")
            context = browser.contexts[0]
        else:
            logger.debug("Creating a new browser context.")
            context = await browser.new_context(
                viewport=self.config.browser_window_size,
                no_viewport=False,
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36"
                ),
                java_script_enabled=True,
                bypass_csp=self.config.disable_security,
                ignore_https_errors=self.config.disable_security,
                record_video_dir=self.config.save_recording_path,
                record_video_size=self.config.browser_window_size,
            )

        # Start tracing if configured
        if self.config.trace_path:
            logger.debug(f"Starting trace, output path: {self.config.trace_path}")
            await context.tracing.start(screenshots=True, snapshots=True, sources=True)

        # Load cookies if file exists
        if self.config.cookies_file and os.path.exists(self.config.cookies_file):
            try:
                with open(self.config.cookies_file, "r", encoding="utf-8") as f:
                    cookies = json.load(f)
                logger.info(
                    f"Loaded {len(cookies)} cookies from {self.config.cookies_file}"
                )
                await context.add_cookies(cookies)
            except (OSError, json.JSONDecodeError) as e:
                logger.warning(
                    f"Failed to load cookies from {self.config.cookies_file}: {e}"
                )

        # Expose anti-detection scripts
        logger.debug("Injecting anti-detection scripts into the browser context.")
        await context.add_init_script(
            """
            // Webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // Languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });

            // Plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            // Chrome runtime
            window.chrome = { runtime: {} };

            // Permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            """
        )

        return context
