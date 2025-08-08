# After processing all PDFs and building the dataframe:
df = pd.DataFrame(all_data)

st.success(f"✅ Extracted {len(df)} valid activities from {len(uploaded_files)} file(s).")

# Buttons to toggle views
show_data = st.button("📋 View Extracted Data Table")
show_repeats = st.button("🔁 View Repeated Activities Table")
show_status = st.button("📤 View Upload Summary")

# ===========================
# 📋 Extracted Data Table
# ===========================
if show_data:
    with st.expander("📋 Extracted Data Table"):
        st.dataframe(df, use_container_width=True)

# ===========================
# 🔁 Categorize and Compare Repeated Activities
# ===========================
def categorize_activity(name):
    name = name.lower()
    if any(word in name for word in ["clear", "grade", "trench", "backfill", "earthwork", "site"]):
        return "🏗 Site Work & Earthwork"
    elif any(word in name for word in ["foundation", "slab", "footing", "structural"]):
        return "🧱 Foundation & Structural"
    elif any(word in name for word in ["tank", "dispenser", "piping", "fuel", "gas"]):
        return "⚙️ Fuel System Installation"
    elif any(word in name for word in ["building", "framing", "roof", "wall", "interior"]):
        return "🛠️ Building Construction"
    elif any(word in name for word in ["landscape", "sidewalk", "curb", "paving", "striping"]):
        return "🌿 Landscaping & Finishing"
    elif any(word in name for word in ["inspection", "punchlist", "handover", "final"]):
        return "📋 Final Inspection & Handover"
    else:
        return "❓ Uncategorized"

dup_ids = df["Activity ID"][df["Activity ID"].duplicated(keep=False)]
repeated_df = df[df["Activity ID"].isin(dup_ids)]

if not repeated_df.empty and show_repeats:
    st.subheader("🔁 Repeated Activities Comparison by Construction Phase")

    # Add a 'Phase' column
    repeated_df["Phase"] = repeated_df["Activity Name"].apply(categorize_activity)

    # Sort for grouping
    repeated_df = repeated_df.sort_values(by=["Phase", "Activity ID", "Project Code", "Start Date"])

    # Group by Phase, then Activity ID & Name
    phase_grouped = repeated_df.groupby(["Phase", "Activity ID", "Activity Name"])

    current_phase = None
    for (phase, act_id, act_name), group in phase_grouped:
        if current_phase != phase:
            st.markdown(f"### {phase}")
            current_phase = phase

        with st.expander(f"🔁 {act_id} — {act_name}"):
            display_df = group[[
                "Project Code", "Project Name", "Duration",
                "Start Date", "Finish Date", "Float", "Notes"
            ]].reset_index(drop=True)
            st.dataframe(display_df, use_container_width=True)
elif show_repeats:
    st.info("✅ No repeated activities found across files.")

# ===========================
# 📤 Upload Summary (Skipped Lines)
# ===========================
if total_skipped and show_status:
    with st.expander("📤 Upload Summary (Skipped Lines)"):
        st.warning(f"⚠️ Skipped {len(total_skipped)} line(s) due to format issues.")
        skipped_df = pd.DataFrame(total_skipped)
        skipped_csv_path = os.path.join(tempfile.gettempdir(), "skipped_lines.csv")
        skipped_df.to_csv(skipped_csv_path, index=False)
        st.download_button(
            "⬇️ Download Skipped Lines CSV",
            data=open(skipped_csv_path, "rb"),
            file_name="skipped_lines.csv",
            mime="text/csv"
        )

# ===========================
# Upload CSV Button (unchanged)
# ===========================
with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_csv:
    df.to_csv(tmp_csv.name, index=False)
    csv_path = tmp_csv.name

csv_filename = "combined_activity_data.csv"

if st.button("📤 Upload Combined Table to Google Drive"):
    try:
        file_id = upload_csv_to_drive(csv_path, csv_filename, folder_id=DRIVE_FOLDER_ID)
        st.success(f"✅ Uploaded! [View File](https://drive.google.com/file/d/{file_id})")
    except Exception as e:
        st.error(f"❌ Upload failed: {str(e)}")
