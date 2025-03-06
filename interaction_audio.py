import asyncio
from playwright.async_api import async_playwright
import base64
import io
import os
import sounddevice as sd
import soundfile as sf
import shutil

AUDIO_PATH = r"E:\Nvidia Videos\videos\yifu.mp3"
FIXED_TEXT_2 = "那个，天气冷了，你要多穿衣服啊。"

"""
    r"D:\GPT-SoVITS-v3lora-20250228\GPT-SoVITS-v3lora-20250228\GPT-SoVITS-v3lora-20250228\TEMP\gradio"
    设置None在不小心点了y可以不删除任何文件
"""
REMOVE_PATH = None

LANGUAGE_OPTIONS = [
    "中文",      # 1
    "英文",      # 2
    "日文",      # 3
    "粤语",      # 4
    "中英混合",  # 5
    "日英混合",  # 6
    "多语种混合"  # 7
]
CUT_METHOD_OPTIONS = [
    "不切",            # 1
    "凑四句一切",       # 2
    "凑50字一切",       # 3
    "按中文句号。切",   # 4
    "按英文句号.切",    # 5
    "按标点符号切"      # 6
    # 如果还有别的切分方式，可以继续加
]

async def setup_reference(page):
    """
    只执行一次：
      1) 设置「参考文本」和「参考音频」。
      2) 选择「合成语种」。
      3) 选择「切分方法」。
      4) 设置 top_k。
    """
    print("[调试] 开始设置参考文本和上传参考音频...")
    await page.fill("#component-15 textarea", FIXED_TEXT_2)
    await page.set_input_files("input[data-testid='file-upload']", AUDIO_PATH)
    await asyncio.sleep(1)
    print("[调试] 参考文本和参考音频已完成设置。😊👌")

    # === 2) 选择合成语种 ===
    print("\n可选语种：")
    for i, lang in enumerate(LANGUAGE_OPTIONS, start=1):
        print(f"  {i}. {lang}")
    while True:
        try:
            lang_choice = int(input("请选择合成语种(输入数字 1~7)："))
            if 1 <= lang_choice <= len(LANGUAGE_OPTIONS):
                break
            else:
                print("超出范围，请重新输入。")
        except ValueError:
            print("无效输入，请输入数字。")

    language_str = LANGUAGE_OPTIONS[lang_choice - 1]
    print(f"你选择了：{language_str}")

    # 调用 set_listbox_value 设置语种
    await set_listbox_value(page, language_str)

    # === 3) 选择切分方法 ===
    print("\n可选切分方法：")
    for i, method in enumerate(CUT_METHOD_OPTIONS, start=1):
        print(f"  {i}. {method}")
    while True:
        try:
            method_choice = int(input("请选择切分方法(输入数字 1~{} )：".format(len(CUT_METHOD_OPTIONS))))
            if 1 <= method_choice <= len(CUT_METHOD_OPTIONS):
                break
            else:
                print("超出范围，请重新输入。")
        except ValueError:
            print("无效输入，请输入数字。")

    method_str = CUT_METHOD_OPTIONS[method_choice - 1]
    print(f"你选择了切分方法：{method_str}")

    # 调用 set_cut_method 设置切分方式
    await set_cut_method(page, method_str)

    # === 4) 设置 top_k ===
    while True:
        try:
            top_k = int(input("\n请输入 top_k (1~100)："))
            if 1 <= top_k <= 100:
                break
            else:
                print("超出范围，请重新输入。")
        except ValueError:
            print("无效输入，请输入数字。")

    print(f"你选择了 top_k = {top_k}")
    await set_top_k(page, top_k)

    # === 5) 设置 top_p ===
    while True:
        try:
            top_p = float(input("\n请输入 top_p (0~1)："))
            if 0 <= top_p <= 1:
                break
            else:
                print("超出范围，请重新输入。")
        except ValueError:
            print("无效输入，请输入数字。")

    print(f"你选择了 top_p = {top_p}")
    await set_top_p(page, top_p)


    # === 6) 设置 temperature ===
    while True:
        try:
            temperature = float(input("\n请输入 temperature (0~1)："))
            if 0 <= temperature <= 1:
                break
            else:
                print("超出范围，请重新输入。")
        except ValueError:
            print("无效输入，请输入数字。")

    print(f"你选择了 temperature = {temperature}")
    await set_temperature(page, temperature)




async def set_listbox_value(page, language_str: str):
    """
    设置 #component-31 这个下拉框的值为 language_str
    """
    # 1) 点击下拉区域，展开选项
    await page.click("#component-31 .secondary-wrap")

    # 2) 等待下拉容器出现
    await page.wait_for_selector("ul.options[role='listbox']", state="visible")

    # 3) 根据 aria-label 匹配 <li>
    selector = f"li[role='option'][aria-label='{language_str}']"
    await page.click(selector)

    # 给前端一点时间刷新UI
    await asyncio.sleep(0.5)

async def set_cut_method(page, method_str: str):
    """
    设置 #component-32 这个下拉框的值为 method_str
    """
    # 1) 点击下拉区域，展开选项
    await page.click("#component-32 .secondary-wrap")

    # 2) 等待下拉容器出现
    await page.wait_for_selector("ul.options[role='listbox']", state="visible")

    # 3) 根据 aria-label 匹配 <li>
    selector = f"li[role='option'][aria-label='{method_str}']"
    await page.click(selector)

    # 给前端一点时间刷新UI
    await asyncio.sleep(0.5)

async def set_top_k(page, top_k: float):
    """
    设置 #component-40 这个横向拉拽组件 (range slider + number input) 的值。
    前端有两个元素：
      - <input type="number" data-testid="number-input" aria-label="number input for top_k">
      - <input type="range" id="range_id_2" ... aria-label="range slider for top_k">
    一般直接填写数字输入框就能同步 slider。
    """
    # 确保 top_k 在 1~100 范围内
    top_k = max(1, min(100, top_k))

    # 方式一：填写数字输入框
    await page.fill("input[aria-label='number input for top_k']", str(top_k))

    # 如果需要也可以同时填 range slider (通常不需要)
    # await page.fill("input[aria-label='range slider for top_k']", str(top_k))

    # 给前端一点时间同步
    await asyncio.sleep(0.5)

async def set_top_p(page, top_p: int):
    """
    设置 #component-41 这个横向拉拽组件 (range slider + number input) 的值。
    前端有两个元素：
      - <input type="number" data-testid="number-input" aria-label="number input for top_p">
      - <input type="range" id="range_id_2" ... aria-label="range slider for top_p">
    一般直接填写数字输入框就能同步 slider。
    """
    # 确保 top_p 在 0~1 范围内
    top_p = max(0, min(1, top_p))

    # 方式一：填写数字输入框
    await page.fill("input[aria-label='number input for top_p']", str(top_p))

    # 如果需要也可以同时填 range slider (通常不需要)
    # await page.fill("input[aria-label='range slider for top_p']", str(top_p))

    # 给前端一点时间同步
    await asyncio.sleep(0.5)


async def set_temperature(page, temperature: float):
    """
    设置 #component-40 这个横向拉拽组件 (range slider + number input) 的值。
    前端有两个元素：
      - <input type="number" data-testid="number-input" aria-label="number input for temperature">
      - <input type="range" id="range_id_2" ... aria-label="range slider for temperature">
    一般直接填写数字输入框就能同步 slider。
    """
    # 确保 temperature 在 0~1 范围内
    temperature = max(0, min(1, temperature))

    # 方式一：填写数字输入框
    await page.fill("input[aria-label='number input for temperature']", str(temperature))

    # 如果需要也可以同时填 range slider (通常不需要)
    # await page.fill("input[aria-label='range slider for temperature']", str(temperature))

    # 给前端一点时间同步
    await asyncio.sleep(0.5)

    
async def synthesize_once(page, user_text, old_src):
    """
    1) 填写「需要合成的文本」（#component-28 textarea）
    2) 点击「合成语音」按钮 (#component-47)
    3) 等待 <audio> 元素出现
    4) 获取其 src (可能是 data: 或 blob:) 并返回
    """
    print(f"[调试] 开始合成文本ing~ 🐾🐾🐾")
    await page.fill("#component-28 textarea", user_text)

    # 点击合成按钮
    await page.click("#component-47")

    while True:
        try:
            # 这里给 5 分钟超时
            await page.wait_for_selector("#component-48 audio", state="attached", timeout=300000)
        except:
            print("超过5分钟，语音合成仍未完成，放弃。")
            return None, old_src

        audio_src = await page.get_attribute("#component-48 audio", "src")
        if audio_src != old_src:
            # 说明出现了新的音频
            old_src = audio_src
            return audio_src, old_src

async def blob_to_base64(page, blob_url: str) -> str:
    """
    在浏览器里fetch(blobUrl)，得到ArrayBuffer后再转base64。
    返回的base64不带 'data:audio/wav;base64,' 前缀
    """
    js_code = f"""
    async () => {{
        const resp = await fetch("{blob_url}");
        const ab = await resp.arrayBuffer();
        const bytes = new Uint8Array(ab);
        let binary = '';
        for (let i = 0; i < bytes.length; i++) {{
            binary += String.fromCharCode(bytes[i]);
        }}
        return btoa(binary);
    }}
    """
    b64_data = await page.evaluate(js_code)
    return b64_data

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto("http://localhost:9872/")

        # === 1) 先设置参考音频、参考文本、语种、切分方法和 top_k (只做一次) ===
        await setup_reference(page)

        old_src = ""

        # === 2) 循环让用户输入要合成的文本 ===
        while True:
            text = input("\n请输入要合成的文本 🤗(输入 'exit' 退出)：")
            if text.lower() == "exit":
                break

            # 调用合成
            audio_src, old_src = await synthesize_once(page, text, old_src)
            if not audio_src:
                print("未获取到音频src!")
                continue
            masked_audio_src = "***" + audio_src.split("-")[-1]
            print("音频 src =>", masked_audio_src)

            # 区分 data:audio/wav;base64 与 blob:
            if audio_src.startswith("data:audio/wav;base64,"):
                prefix = "data:audio/wav;base64,"
                b64_data = audio_src[len(prefix):]
                wav_bytes = base64.b64decode(b64_data)
            elif audio_src.startswith("blob:"):
                b64_data = await blob_to_base64(page, audio_src)
                wav_bytes = base64.b64decode(b64_data)
            else:
                print("音频不是 data:audio/wav;base64 也不是 blob:，无法处理！")
                continue

            # 解码并播放
            try:
                data, samplerate = sf.read(io.BytesIO(wav_bytes))
                print(f"采样率: {samplerate}, shape={data.shape}")
                sd.play(data, samplerate=samplerate)
                sd.wait()
            except Exception as e:
                print("音频解码失败:", e)

        await browser.close()

    text = input("是否删除已生成音频的文件?(y/n) 🤔\n")
    while True:
        try:
            if text.lower() == "y":
                shutil.rmtree(REMOVE_PATH)
                os.makedirs(REMOVE_PATH)
                return
            elif text.lower() == "n":
                return
            else:
                print("无效输入，重新输入。")
        except Exception as e:
            print("路径格式错误:", e)
            return

if __name__ == "__main__":
    asyncio.run(main())
