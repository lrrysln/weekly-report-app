        float_threshold = st.slider("Highlight tasks with float ≤", 0, 20, 5)
        critical_df = project_df[project_df["Float"] <= float_threshold]

        if not critical_df.empty:
            st.warning(f"⚠️ {len(critical_df)} task(s) have float ≤ {float_threshold} days.")

            def highlight_weather_delay(row):
                if row['Weather Delay Risk']:
                    return ['background-color: yellow'] * len(row)
                else:
                    return [''] * len(row)

            st.dataframe(
                critical_df[[
                    "Project Code", "Project Name", "Activity ID", "Activity Name",
                    "Duration", "Start Date", "Finish Date", "Float", "Notes", "Weather Delay Risk"
                ]].style.apply(highlight_weather_delay, axis=1),
                use_container_width=True
            )
        else:
            st.success("✅ No critical tasks found with the selected float threshold.")

    # Tab 4: Upload
    with tabs[3]:
        st.header("📤 Upload Extracted Data to Google Drive")
        csv_name = f"Activity_Data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        temp_path = os.path.join(tempfile.gettempdir(), csv_name)
        df.to_csv(temp_path, index=False)

        with open(temp_path, "rb") as file:
            st.download_button("⬇️ Download CSV", data=file, file_name=csv_name)

        if st.button("📤 Upload CSV to Google Drive"):
            try:
                file_id = upload_csv_to_drive(temp_path, csv_name, folder_id=DRIVE_FOLDER_ID)
                st.success(f"✅ Uploaded to Google Drive (File ID: {file_id})")
            except Exception as e:
                st.error(f"❌ Failed to upload: {e}")

    # Tab 5: PDF Reports
    with tabs[4]:
        st.header("📄 Generate PDF Report")
        if st.button("📥 Create PDF Summary Report"):
            pdf_path = create_pdf_report(df, critical_df, selected_project)
            with open(pdf_path, "rb") as pdf_file:
                st.download_button("⬇️ Download Report", data=pdf_file, file_name=os.path.basename(pdf_path))
