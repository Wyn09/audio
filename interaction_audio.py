# interaction_audio.py

import asyncio
from playwright.async_api import async_playwright
import sounddevice as sd
import soundfile as sf
import io

# 你自己的本地音频文件路径
AUDIO_PATH = r"E:\Nvidia Videos\videos\yifu.mp3"
# 第二个文本框的固定内容
FIXED_TEXT_2 = "那个，天气冷了，你要多穿衣服啊。"

async def generate_audio(page, text1):
    """
    1) 填写第一个文本框 #input_text1
    2) 填写第二个文本框 #input_text2 (固定内容)
    3) 上传本地音频
    4) 点击Generate
    5) 等待并返回下载链接
    """
    # 1) 填充第一个文本框
    await page.fill('#input_text1 textarea', text1)
    
    # 2) 填充第二个文本框
    await page.fill('#input_text2 textarea', FIXED_TEXT_2)

    # 3) 给音频上传控件设置文件
    #    你在 HTML 里可以看到: <input type="file" ... accept="audio/*">
    #    只要选对了那个 <input>, 就能上传
    await page.set_input_files("input[type='file']", AUDIO_PATH)

    # 4) 点击Generate按钮
    await page.click('#button')

    # 5) 等待下载链接
    await page.wait_for_selector(".download-link", state="attached")
    download_link = await page.get_attribute(".download-link", "href")
    return download_link

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        await page.goto('http://127.0.0.1:7860/')

        while True:
            text1 = input("请输入文本1（输入 'exit' 退出）：")
            if text1.lower() == 'exit':
                break

            wav_url = await generate_audio(page, text1)
            if not wav_url:
                print("未获取到有效的音频下载链接！")
                continue

            print("音频下载链接:", wav_url)

            # Playwright 自带请求，去下载 wav 文件
            response = await page.request.get(wav_url)
            if response.status != 200:
                print(f"下载失败，HTTP状态码: {response.status}")
                continue

            # 解码成音频并播放
            wav_bytes = await response.body()
            data, samplerate = sf.read(io.BytesIO(wav_bytes))
            print(f"采样率: {samplerate}, 波形 shape: {data.shape}")
            sd.play(data, samplerate=samplerate)
            sd.wait()

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
