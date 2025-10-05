# app.py
import streamlit as st
import json
import os
from pathlib import Path
import datetime

# -------- CONFIG ----------
MANIFEST_FILE = "manifest.json"
STATIC_DIR = "static"
# --------------------------

st.set_page_config(page_title="Engineering Study Materials", layout="wide")

# ---------- UTILITY FUNCTIONS ----------
def ensure_dirs():
    Path(STATIC_DIR).mkdir(parents=True, exist_ok=True)
    if not Path(MANIFEST_FILE).exists():
        with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
            json.dump({"years": []}, f, indent=2, ensure_ascii=False)

def load_manifest():
    ensure_dirs()
    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_manifest(manifest):
    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

def unique_filename(folder: Path, name: str) -> str:
    base, ext = os.path.splitext(name)
    counter, candidate = 1, f"{base}{ext}"
    while (folder / candidate).exists():
        candidate = f"{base}_{counter}{ext}"
        counter += 1
    return candidate

# ---------- FIND OR CREATE ----------
def find_or_create_year(manifest, year_name):
    for y in manifest["years"]:
        if y["name"] == year_name:
            return y
    new = {"name": year_name, "branches": []}
    manifest["years"].append(new)
    return new

def find_or_create_branch(year_obj, branch_name):
    for b in year_obj["branches"]:
        if b["name"] == branch_name:
            return b
    new = {"name": branch_name, "subjects": []}
    year_obj["branches"].append(new)
    return new

def find_or_create_subject(branch_obj, subject_name):
    for s in branch_obj["subjects"]:
        if s["name"] == subject_name:
            return s
    new = {"name": subject_name, "resources": []}
    branch_obj["subjects"].append(new)
    return new

def add_resource(manifest, year_name, branch_name, subject_name, resource):
    year_obj = find_or_create_year(manifest, year_name)
    branch_obj = find_or_create_branch(year_obj, branch_name)
    subject_obj = find_or_create_subject(branch_obj, subject_name)
    subject_obj["resources"].append(resource)
    save_manifest(manifest)

# ---------- FLATTEN ----------
def flatten_resources(manifest):
    flat = []
    for year in manifest["years"]:
        for branch in year.get("branches", []):
            for subject in branch.get("subjects", []):
                for res in subject.get("resources", []):
                    flat.append({
                        "year": year["name"],
                        "branch": branch["name"],
                        "subject": subject["name"],
                        "title": res.get("title"),
                        "type": res.get("type"),
                        "url": res.get("url"),
                        "path": res.get("path"),
                    })
    return flat

# ---------- UI ----------
st.title("📚 Engineering Study Materials")
manifest = load_manifest()

col1, col2 = st.columns([3, 1])

with col2:
    st.header("Controls")
    admin_mode = st.checkbox("Admin mode (Add/Edit/Delete)", value=False)
    if admin_mode:
        st.info("⚙️ Admin mode enabled. Add, Edit, or Delete items.")
    st.markdown("---")
    if st.button("Download manifest JSON"):
        with open(MANIFEST_FILE, "rb") as f:
            st.download_button("Click to download manifest.json", f.read(), file_name="manifest.json")

with col1:
    q = st.text_input("🔎 Search (title / subject / branch / year)", value="", placeholder="e.g. Signals, 2nd Year, ECE")

# ---------- ADD NEW ----------
if admin_mode:
    st.markdown("## ➕ Add New Resource")
    with st.form("add_resource_form", clear_on_submit=True):
        year_name = st.text_input("Year (e.g. 1st Year, 2nd Year)")
        branch_name = st.text_input("Branch (e.g. CSE, ECE or 'Common')")
        subject_name = st.text_input("Subject (e.g. Mathematics, Signals)")
        title = st.text_input("Resource Title")
        res_type = st.selectbox("Resource Type", ["link", "upload_file"])
        url, uploaded_file = "", None

        if res_type == "link":
            url = st.text_input("URL (Google Drive or public link)")
        else:
            uploaded_file = st.file_uploader("Upload file", accept_multiple_files=False)

        submitted = st.form_submit_button("Add Resource")
        if submitted:
            if not (year_name and branch_name and subject_name and title):
                st.error("Please fill all required fields.")
            else:
                if res_type == "link" and not url:
                    st.error("Please provide a link URL.")
                else:
                    ensure_dirs()
                    if res_type == "file":
                        folder = Path(STATIC_DIR)
                        safe_name = unique_filename(folder, uploaded_file.name)
                        save_path = folder / safe_name
                        with open(save_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        resource = {
                            "title": title,
                            "type": "file",
                            "path": f"{STATIC_DIR}/{safe_name}",
                            "meta": {"added": str(datetime.datetime.utcnow())}
                        }
                    else:
                        resource = {"title": title, "type": "link", "url": url, "meta": {"added": str(datetime.datetime.utcnow())}}
                    add_resource(manifest, year_name.strip(), branch_name.strip(), subject_name.strip(), resource)
                    st.success("✅ Resource added successfully!")

# ---------- DISPLAY ----------
st.markdown("---")

if q:
    st.markdown(f"### 🔍 Search Results for: `{q}`")
    ql = q.lower()
    results = [r for r in flatten_resources(manifest)
               if ql in r["title"].lower()
               or ql in r["subject"].lower()
               or ql in r["branch"].lower()
               or ql in r["year"].lower()]
    if not results:
        st.info("No results found.")
    else:
        for r in results:
            st.write(f"**{r['title']}** — {r['year']} / {r['branch']} / {r['subject']}")
            if r["type"] == "link":
                st.markdown(f"[🔗 Open Link]({r['url']})")
            else:
                with open(r["path"], "rb") as f:
                    data = f.read()
                    st.download_button("⬇️ Download File", data, file_name=os.path.basename(r["path"]))
else:
    st.markdown("## 📁 Browse Materials")
    for year in manifest.get("years", []):
        with st.expander(f"📅 {year['name']}", expanded=False):
            # Year edit/delete
            if admin_mode:
                edit_year = st.text_input(f"✏️ Rename Year ({year['name']})", value=year["name"], key=f"edit_year_{year['name']}")
                if edit_year != year["name"]:
                    year["name"] = edit_year
                    save_manifest(manifest)
                    st.success("✅ Year renamed.")
                    st.experimental_rerun()
                if st.button(f"🗑️ Delete {year['name']}", key=f"delete_year_{year['name']}"):
                    manifest["years"].remove(year)
                    save_manifest(manifest)
                    st.warning("❌ Year deleted.")
                    st.experimental_rerun()

            for branch in year.get("branches", []):
                with st.expander(f"🏷️ {branch['name']}", expanded=False):
                    # Branch edit/delete
                    if admin_mode:
                        edit_branch = st.text_input(f"✏️ Rename Branch ({branch['name']})", value=branch["name"], key=f"edit_branch_{year['name']}_{branch['name']}")
                        if edit_branch != branch["name"]:
                            branch["name"] = edit_branch
                            save_manifest(manifest)
                            st.success("✅ Branch renamed.")
                            st.experimental_rerun()
                        if st.button(f"🗑️ Delete Branch {branch['name']}", key=f"delete_branch_{year['name']}_{branch['name']}"):
                            year["branches"].remove(branch)
                            save_manifest(manifest)
                            st.warning("❌ Branch deleted.")
                            st.experimental_rerun()

                    for subject in branch.get("subjects", []):
                        with st.expander(f"📘 {subject['name']}", expanded=False):
                            # Subject edit/delete
                            if admin_mode:
                                edit_subject = st.text_input(f"✏️ Rename Subject ({subject['name']})", value=subject["name"], key=f"edit_subject_{year['name']}_{branch['name']}_{subject['name']}")
                                if edit_subject != subject["name"]:
                                    subject["name"] = edit_subject
                                    save_manifest(manifest)
                                    st.success("✅ Subject renamed.")
                                    st.experimental_rerun()
                                if st.button(f"🗑️ Delete Subject {subject['name']}", key=f"delete_subject_{year['name']}_{branch['name']}_{subject['name']}"):
                                    branch["subjects"].remove(subject)
                                    save_manifest(manifest)
                                    st.warning("❌ Subject deleted.")
                                    st.experimental_rerun()

                            for res in subject.get("resources", []):
                                st.write(f"**{res['title']}**")
                                if res["type"] == "link":
                                    st.markdown(f"[🔗 Open Link]({res['url']})")
                                else:
                                    p = res["path"]
                                    with open(p, "rb") as f:
                                        data = f.read()
                                        st.download_button("⬇️ Download", data, file_name=os.path.basename(p))
                                # Resource edit/delete
                                if admin_mode:
                                    new_title = st.text_input(f"✏️ Edit Title ({res['title']})", value=res["title"], key=f"edit_res_{year['name']}_{branch['name']}_{subject['name']}_{res['title']}")
                                    if new_title != res["title"]:
                                        res["title"] = new_title
                                        save_manifest(manifest)
                                        st.success("✅ Resource title updated.")
                                        st.experimental_rerun()
                                    if st.button(f"🗑️ Delete {res['title']}", key=f"delete_res_{year['name']}_{branch['name']}_{subject['name']}_{res['title']}"):
                                        if res["type"] == "file" and os.path.exists(res.get("path", "")):
                                            os.remove(res["path"])
                                        subject["resources"].remove(res)
                                        save_manifest(manifest)
                                        st.warning("❌ Resource deleted.")
                                        st.experimental_rerun()

st.markdown("---")
st.caption("Tip: Use Admin mode to manage items. For Drive files, use public share links.")
