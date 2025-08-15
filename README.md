# LocVi

LocVi is a lightweight Flask-based local file browser that lets you poke around your files, watch videos, listen to audio, and view images without losing your mind.
It remembers recent folders and the last file you opened… because we all forget stuff.

Might add more features someday… maybe, or not.

### LocVi Demo Gallery

| Screenshot 1 | Screenshot 2 | Screenshot 3 |
|--------------|--------------|--------------|
| ![Screenshot 1](https://github.com/user-attachments/assets/93170fd6-b96b-4e12-baac-1145957b6c2d) | ![Screenshot 2](https://github.com/user-attachments/assets/a039a4d5-bde6-4589-83a2-feca6d4d0084) | ![Screenshot 3](https://github.com/user-attachments/assets/cd596236-e1d4-443c-a1bd-19126a53375c) |

| Screenshot 4 | Screenshot 5 |
|--------------|--------------|
| ![Screenshot 4](https://github.com/user-attachments/assets/80f16c2e-0d87-488e-bd94-000fcdc381b0) | ![Screenshot 5](https://github.com/user-attachments/assets/4f016bf3-091d-4fdf-9163-04388e925c8e) |

| Video Demo YouTube |
|--------------------|
|[![Video](https://img.youtube.com/vi/xjo8wX2ciJY/0.jpg)](https://youtu.be/xjo8wX2ciJY)|

---

### Why I Created It

I have tons of PDFs and other files across multiple subdirectories, and every time I want to read or watch something, I have to open, close, and hunt through folders. It’s annoying. I also often forget what I was reading or watching last, or what I’ve already finished.

So I built a **browser-based preview tool**—basically my attempt to improve on the frustrating Windows File Explorer experience.

---

### What It Does

- Paste any folder path and instantly view all files inside.
- Preview PDFs, videos, audio, images (PNG, JPEG, etc.), and text files.
- Sort files the way you want (default folder sorting is just frustrating).
- Remembers **recently opened folders** and **last viewed file**, inspired by VS Code.
- Checkbox indicator to mark files as “done reading/watching.” State is saved locally in JSON simple but effective.
- Gives hands-on experience with Python backend development while being genuinely useful.

---

### Current Limitations

- For **large folders**, rendering the file list can take a little time.
- Sometimes PDFs open in a **different tab** depending on the browser behavior.
- Does **not yet support large archives** (zip, rar, etc.)—only previews individual files.

---

### What’s Next

I love this project, and I’m thinking of:

- Learn algorithm so I can improve the speed and possible app for it
- Adding **search and filtering** for quick file lookup.
- Supporting more file types and larger files efficiently.
- Maybe a **small recommendation system** for files based on your reading/watching history.
- Learning more **backend concepts** to handle large directories smoothly.
