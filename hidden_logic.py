import asyncio
import random
from playwright.async_api import async_playwright
import indian_names

# Flag to indicate whether the script is running
running = True

# Event to synchronize threads
join_audio_event = asyncio.Event()

# Generate a unique user name
def generate_unique_user():
    first_name = indian_names.get_first_name()
    last_name = indian_names.get_last_name()
    return f"{first_name} {last_name}"

async def start(wait_time, meetingcode, passcode):
    global join_audio_event
    global running

    try:
        # Generate unique user name
        user = generate_unique_user()

        print(f"{user} attempting to join with Chromium.")

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--use-fake-ui-for-media-stream',
                    '--use-fake-device-for-media-stream',
                    f'--disk-cache-size={random.randint(200, 500)}000000',
                    f'--max-active-views={random.randint(5, 15)}'
                ]
            )

            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(f'http://app.zoom.us/wc/join/{meetingcode}', timeout=200000)

            # Skip automatic media permissions (audio/video requests)
            # await page.evaluate('() => { navigator.mediaDevices.getUserMedia({ audio: true, video: true }); }')

            try:
                await page.click('//button[@id="onetrust-accept-btn-handler"]', timeout=5000)
            except Exception:
                pass

            try:
                await page.click('//button[@id="wc_agree1"]', timeout=5000)
            except Exception:
                pass

            try:
                await page.wait_for_selector('input[type="text"]', timeout=200000)
                await page.fill('input[type="text"]', user)

                password_field_exists = await page.query_selector('input[type="password"]')
                if password_field_exists:
                    await page.fill('input[type="password"]', passcode)
                    join_button = await page.wait_for_selector('button.preview-join-button', timeout=200000)
                    await join_button.click()
                else:
                    join_button = await page.wait_for_selector('button.preview-join-button', timeout=200000)
                    await join_button.click()
            except Exception:
                pass

            retry_count = 5
            while retry_count > 0:
                try:
                    await page.wait_for_selector('button.join-audio-by-voip__join-btn', timeout=300000)
                    query = 'button[class*="join-audio-by-voip__join-btn"]'
                    mic_button_locator = await page.query_selector(query)
                    await asyncio.sleep(2)
                    await mic_button_locator.evaluate_handle('node => node.click()')
                    print(f"{user} successfully joined audio.")

                    join_audio_event.set()
                    break
                except Exception as e:
                    print(f"Attempt {5 - retry_count + 1}: {user} failed to join audio. Retrying...", e)
                    retry_count -= 1
                    await asyncio.sleep(2)

            if retry_count == 0:
                print(f"{user} failed to join audio after multiple attempts.")

            # Do not request or enable video automatically
            print(f"{user} will remain in the meeting for {wait_time} seconds ...")
            while running and wait_time > 0:
                await asyncio.sleep(1)
                wait_time -= 1
            print(f"{user} has left the meeting.")

        await context.close()
        await browser.close()

    except Exception as e:
        print(f"An error occurred: {e}")
