# traumakom Prompt Generator – ComfyUI Node

A powerful custom node for ComfyUI that generates rich, dynamic prompts based on modular JSON worlds — with color realm control (RGB / CMYK), LoRA triggers, and optional AI-based prompt enhancement.

> Created with passion by [traumakom](https://github.com/traumakom)  
> Powered by Dante 🐈‍⬛, Helly 🐺, and Lily 💻

---

<img width="581" height="657" alt="image" src="https://github.com/user-attachments/assets/5382f908-2999-4cf0-9763-2af880990c93" />


## 🌟 Features

- 🔮 Dynamic prompt generation from modular JSON worlds
- 🎨 `COLOR_REALM` support for RGB / CMYK palette-driven aesthetics
- 🧠 Optional AI enhancer using OpenAI, Cohere, or Gemini
- 🧩 LoRA trigger integration (e.g., `Realistic`, `Detailed Hand`)
- 📁 Reads world data from `/JSON_DATA`
- 🧪 Debug messages and error handling for smooth workflow

---

## 📦 Installation

### 🔸 Option 1: Using ComfyUI Manager
1. Open ComfyUI → `Manager` tab
2. Click `Install from URL`
3. Paste the GitHub repo link and hit Install

### 🔸 Option 2: Manual Install
```bash
cd ComfyUI/custom_nodes
git clone https://github.com/yourusername/PromptCreatorNode.git
```

---

## 📁 Folder Structure

```
ComfyUI/
├── custom_nodes/
│   └── PromptCreatorNode/
│       └── PromptCreatorNode.py
├── JSON_DATA/
│   ├── RGB_Chronicles.json
│   ├── CMYK_Chronicles.json
│   └── ...
├── api_keys.txt
```

> ✅ `api_keys.txt` is a **simple text file**, **not** JSON. Example:

```
openai=sk-...
cohere=...
gemini=...
```

---

## ⚙️ How to Use

1. Open ComfyUI and search for the **PromptCreator** node
2. Choose one of the installed JSON worlds from the dropdown (e.g. `RGB_Chronicles`)
3. Optionally enable AI Enhancement (OpenAI / Cohere / Gemini)
4. Click **Generate Prompt**
5. Connect the output to `CLIPTextEncode` or use however you'd like!

---

## 🧪 Prompt Enhancement

When selected, the enhancer will transform your raw prompt into a refined, vivid description using:

- **OpenAI** (GPT-3.5-turbo)
- **Cohere** (Command R+)
- **Gemini** (Gemini 2.5 Pro)

> Make sure to place the correct API key in `api_keys.txt`.

---

## 🌈 JSON World Format

Each `.json` file includes categories like:

- `COLOR_REALM`: Defines the active color palette (e.g. ["C", "M", "Y", "K"])
- Realm-specific values: `OUTFITS`, `LIGHTING`, `BACKGROUNDS`, `OBJECTS`, `ACCESSORIES`, `ATMOSPHERES`
- Global traits: `EPOCHS`, `POSES`, `EXPRESSIONS`, `CAMERA_ANGLES`, `HORROR_INTENSITY`

JSON files must be saved inside the `ComfyUI/JSON_DATA/` folder.

---

## 🖼️ Example Output

Generated using the CMYK Realm:

> “A beautiful woman wearing a shadow-ink kimono, standing in a forgotten monochrome realm, surrounded by voidstorm pressure and carrying an inkborn scythe.”

---

## ☕ Support My Work

If you enjoy this project, consider buying me a coffee on Ko-Fi:  
[https://ko-fi.com/traumakom](https://ko-fi.com/traumakom)


## 🙏 Credits

Thanks to:

- **Magnificent Lily** 💻  
- **My wonderful cat Dante** 😽  
- **My one and only muse Helly** 😍❤️❤️❤️😍

---

## 📜 License

Free to use and remix.  
If you love it, ⭐ star the repo or ☕ donate a coffee!

Let the prompt alchemy begin 🧪✨
