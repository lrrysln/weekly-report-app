    all_data = []
    total_skipped = []

    for uploaded_file in uploaded_files:
        pdf_name = os.path.splitext(uploaded_file.name)[0]
        st.info(f"📄 Processing: `{uploaded_file.name}`")

        # Extract project metadata
        title_parts = pdf_name.split(" - ")
        project_code = title_parts[0].strip() if len(title_parts) > 0 else "Unknown"
        project_name = title_parts[1].strip().title() if len(title_parts) > 1 else "Unknown Project"

        # Extract text
        all_text = ""
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    all_text += page_text + "\n"

        # Regex pattern
        pattern = re.compile(r"^(\S+)\s+(.+?)\s+(\d+)\s+(\d{2}-\d{2}-\d{2})\s+(\d{2}-\d{2}-\d{2})\s+(\d+)\s+(.*)$")
        skipped_lines = []

        for line in all_text.strip().split('\n'):
            line = line.strip()
            match = pattern.match(line)
            if match:
                all_data.append({
                    "Project Code": project_code,
                    "Project Name": project_name,
                    "Activity ID": match.group(1),
                    "Activity Name": match.group(2),
                    "Duration": int(match.group(3)),
                    "Start Date": match.group(4),
                    "Finish Date": match.group(5),
                    "Float": int(match.group(6)),
                    "Notes": match.group(7)
                })
            else:
                skipped_lines.append({"PDF": uploaded_file.name, "Line": line})

        if skipped_lines:
            st.warning(f"⚠️ Skipped {len(skipped_lines)} line(s) in `{uploaded_file.name}` due to format issues.")
            total_skipped.extend(skipped_lines)
            with st.expander(f"🔍 View Skipped Lines for `{uploaded_file.name}`"):
                for item in skipped_lines:
                    st.text(item["Line"])
