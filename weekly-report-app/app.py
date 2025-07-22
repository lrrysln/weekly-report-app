{\rtf1\ansi\ansicpg1252\cocoartf2639
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fmodern\fcharset0 Courier;\f1\fnil\fcharset0 AppleColorEmoji;\f2\fnil\fcharset0 Menlo-Regular;
}
{\colortbl;\red255\green255\blue255;\red195\green123\blue90;\red23\green23\blue26;\red174\green176\blue183;
\red103\green107\blue114;\red89\green158\blue96;\red71\green149\blue242;\red152\green54\blue29;\red117\green114\blue185;
\red38\green157\blue169;\red31\green46\blue49;}
{\*\expandedcolortbl;;\csgenericrgb\c76471\c48235\c35294;\csgenericrgb\c9020\c9020\c10196;\csgenericrgb\c68235\c69020\c71765;
\csgenericrgb\c40392\c41961\c44706;\csgenericrgb\c34902\c61961\c37647;\csgenericrgb\c27843\c58431\c94902;\csgenericrgb\c59608\c21176\c11373;\csgenericrgb\c45882\c44706\c72549;
\csgenericrgb\c14902\c61569\c66275;\csgenericrgb\c12157\c18039\c19216;}
\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\pardirnatural\partightenfactor0

\f0\fs26 \cf2 \cb3 import \cf4 streamlit \cf2 as \cf4 st\
\cf2 import \cf4 pandas \cf2 as \cf4 pd\
\cf2 import \cf4 datetime\
\cf2 import \cf4 re\
\cf2 from \cf4 pathlib \cf2 import \cf4 Path\
\
\cf5 # Paths\
\cf4 DOWNLOADS = Path.home() / \cf6 "Downloads"\
\
\cf5 # Utility functions\
\cf2 def \cf7 get_current_week_folder\cf4 ():\
    today = datetime.datetime.now()\
    week_num = today.isocalendar().week\
    \cf2 return \cf4 DOWNLOADS / \cf6 f"Week \cf2 \{\cf4 week_num\cf2 \} \{\cf4 today.year\cf2 \}\cf6 "\
\
\cf2 def \cf7 get_weekly_filename\cf4 ():\
    today = datetime.datetime.now()\
    week_num = today.isocalendar().week\
    \cf2 return \cf6 f"Week \cf2 \{\cf4 week_num\cf2 \} \{\cf4 today.year\cf2 \}\cf6  Report.html"\
\
\cf2 def \cf7 save_to_excel\cf4 (entry_data):\
    week_folder = get_current_week_folder()\
    week_folder.mkdir(\cf8 parents\cf4 =\cf2 True\cf4 , \cf8 exist_ok\cf4 =\cf2 True\cf4 )\
    existing = \cf9 list\cf4 (week_folder.glob(\cf6 "file*.xlsx"\cf4 ))\
    index = \cf9 len\cf4 (existing) + \cf10 1\
    \cf4 path = week_folder / \cf6 f"file\cf2 \{\cf4 index\cf2 \}\cf6 .xlsx"\
    \cf4 pd.DataFrame([entry_data]).to_excel(path, \cf8 index\cf4 =\cf2 False\cf4 , \cf8 engine\cf4 =\cf6 "openpyxl"\cf4 )\
\
\cf2 def \cf7 generate_weekly_summary\cf4 (password):\
    \cf2 if \cf4 password != \cf6 "1234"\cf4 :\
        \cf2 return None\cf4 , \cf6 "\cf2 \\n
\f1 \cf6 \uc0\u10060 
\f0  Incorrect password."\
    \cf4 week_folder = get_current_week_folder()\
    \cf2 if not \cf4 week_folder.exists():\
        \cf2 return None\cf4 , \cf6 "
\f1 \uc0\u9888 \u65039 
\f0  There have been no entries submitted this week."\
\
    \cf4 files = \cf9 sorted\cf4 (week_folder.glob(\cf6 "file*.xlsx"\cf4 ))\
    \cf2 if not \cf4 files:\
        \cf2 return None\cf4 , \cf6 "
\f1 \uc0\u9888 \u65039 
\f0  There have been no entries submitted this week."\
\
    \cf4 df = pd.concat((pd.read_excel(f, \cf8 engine\cf4 =\cf6 "openpyxl"\cf4 ) \cf2 for \cf4 f \cf2 in \cf4 files), \cf8 ignore_index\cf4 =\cf2 True\cf4 )\
    \cf2 if \cf4 df.empty:\
        \cf2 return None\cf4 , \cf6 "
\f1 \uc0\u55357 \u57003 
\f0  No data to summarize."\
\
    \cf4 df.sort_values(\cf6 "Subject"\cf4 , \cf8 inplace\cf4 =\cf2 True\cf4 )\
\
    html = [\cf6 "<html><head><style>"\cf4 ,\
            \cf6 "body\{font-family:Arial;padding:20px\}"\cf4 ,\
            \cf6 "h1\{text-align:center\}"\cf4 ,\
            \cf6 "h2\{background:#cce5ff;padding:10px;border-radius:4px\}"\cf4 ,\
            \cf6 ".entry\{border:1px solid #ccc;padding:10px;margin:10px 0;border-radius:4px;background:#f9f9f9\}"\cf4 ,\
            \cf6 "ul\{margin:0;padding-left:20px\}"\cf4 ,\
            \cf6 ".label\{font-weight:bold\}"\cf4 ,\
            \cf6 "</style></head><body>"\cf4 ,\
            \cf6 "<h1>Weekly Summary Report</h1>"\cf4 ]\
\
    \cf2 for \cf4 subject, group \cf2 in \cf4 df.groupby(\cf6 "Subject"\cf4 ):\
        html.append(\cf6 f"<h2>\cf2 \{\cf4 subject\cf2 \}\cf6 </h2>"\cf4 )\
        \cf2 for \cf4 _, row \cf2 in \cf4 group.iterrows():\
            html.append(\cf6 '<div class="entry"><ul>'\cf4 )\
            html.append(\cf6 f"<li><span class='label'>Store Name:</span> \cf2 \{\cf4 row.get(\cf6 'Store Name'\cf4 , \cf6 ''\cf4 )\cf2 \}\cf6 </li>"\cf4 )\
            html.append(\cf6 f"<li><span class='label'>Store Number:</span> \cf2 \{\cf4 row.get(\cf6 'Store Number'\cf4 , \cf6 ''\cf4 )\cf2 \}\cf6 </li>"\cf4 )\
\
            types = [col \cf2 for \cf4 col \cf2 in\
                     \cf4 [\cf6 "RaceWay EDO Stores"\cf4 , \cf6 "RT EFC - Traditional"\cf4 , \cf6 "RT 5.5k EDO Stores"\cf4 , \cf6 "RT EFC EDO Stores"\cf4 ,\
                      \cf6 "RT Travel Centers"\cf4 ] \cf2 if \cf4 row.get(col)]\
            \cf2 if \cf4 types:\
                html.append(\cf6 "<li><span class='label'>Types:</span><ul>"\cf4 )\
                html += [\cf6 f"<li>\cf2 \{\cf4 t\cf2 \}\cf6 </li>" \cf2 for \cf4 t \cf2 in \cf4 types]\
                html.append(\cf6 "</ul></li>"\cf4 )\
\
            html.append(\cf6 "<li><span class='label'>Dates:</span><ul>"\cf4 )\
            \cf2 for \cf4 label \cf2 in \cf4 [\cf6 "TCO Date"\cf4 , \cf6 "Ops Walk Date"\cf4 , \cf6 "Turnover Date"\cf4 , \cf6 "Open to Train Date"\cf4 , \cf6 "Store Opening"\cf4 ]:\
                html.append(\cf6 f"<li><span class='label'>\cf2 \{\cf4 label\cf2 \}\cf6 :</span> \cf2 \{\cf4 row.get(label, \cf6 ''\cf4 )\cf2 \}\cf6 </li>"\cf4 )\
            html.append(\cf6 "</ul></li>"\cf4 )\
\
            notes = [\
                re.sub(\cf6 r"\cb11 ^[\\s\'95\\-\'96
\f2 \uc0\u9679 
\f0 ]+\cb3 "\cf4 , \cf6 ""\cf4 , n)\
                \cf2 for \cf4 n \cf2 in \cf9 str\cf4 (row.get(\cf6 "Notes"\cf4 , \cf6 ""\cf4 )).splitlines()\
                \cf2 if \cf4 n.strip()\
            ]\
            \cf2 if \cf4 notes:\
                html.append(\cf6 "<li><span class='label'>Notes:</span><ul>"\cf4 )\
                html += [\cf6 f"<li>\cf2 \{\cf4 n\cf2 \}\cf6 </li>" \cf2 for \cf4 n \cf2 in \cf4 notes]\
                html.append(\cf6 "</ul></li>"\cf4 )\
\
            html.append(\cf6 "</ul></div>"\cf4 )\
\
    html.append(\cf6 "</body></html>"\cf4 )\
    \cf2 return \cf4 df, \cf6 ""\cf4 .join(html)\
\
\cf2 def \cf7 save_html_report\cf4 (html_content):\
    week_folder = get_current_week_folder()\
    week_folder.mkdir(\cf8 parents\cf4 =\cf2 True\cf4 , \cf8 exist_ok\cf4 =\cf2 True\cf4 )\
    filename = get_weekly_filename()\
    path = week_folder / filename\
    \cf2 with \cf9 open\cf4 (path, \cf6 "w"\cf4 , \cf8 encoding\cf4 =\cf6 "utf-8"\cf4 ) \cf2 as \cf4 f:\
        f.write(html_content)\
    \cf2 return \cf4 path\
\
\cf5 # Streamlit UI\
\cf4 st.title(\cf6 "
\f1 \uc0\u55357 \u56541 
\f0  Weekly Store Report Form"\cf4 )\
\
\cf2 with \cf4 st.form(\cf6 "entry_form"\cf4 ):\
    st.subheader(\cf6 "Store Info"\cf4 )\
    store_name = st.text_input(\cf6 "Store Name"\cf4 )\
    store_number = st.text_input(\cf6 "Store Number"\cf4 )\
\
    st.subheader(\cf6 "Project Details"\cf4 )\
    subject = st.selectbox(\cf6 "Subject"\cf4 , [\
        \cf6 "New Construction"\cf4 , \cf6 "EDO Additions"\cf4 , \cf6 "Phase 1/ Demo - New Construction Sites"\cf4 ,\
        \cf6 "Remodels"\cf4 , \cf6 "6k Remodels"\cf4 , \cf6 "EV Project"\cf4 , \cf6 "Traditional Special Project"\cf4 ,\
        \cf6 "Miscellaneous Items of Note"\cf4 , \cf6 "Potential Projects"\cf4 ,\
        \cf6 "Complete - Awaiting Post Completion Site Visit"\cf4 , \cf6 "2025 Completed Projects"\
    \cf4 ])\
\
    st.subheader(\cf6 "Store Types"\cf4 )\
    types = \{\
        \cf6 "RaceWay EDO Stores"\cf4 : st.checkbox(\cf6 "RaceWay EDO Stores"\cf4 ),\
        \cf6 "RT EFC - Traditional"\cf4 : st.checkbox(\cf6 "RT EFC - Traditional"\cf4 ),\
        \cf6 "RT 5.5k EDO Stores"\cf4 : st.checkbox(\cf6 "RT 5.5k EDO Stores"\cf4 ),\
        \cf6 "RT EFC EDO Stores"\cf4 : st.checkbox(\cf6 "RT EFC EDO Stores"\cf4 ),\
        \cf6 "RT Travel Centers"\cf4 : st.checkbox(\cf6 "RT Travel Centers"\cf4 )\
    \}\
\
    st.subheader(\cf6 "Important Dates"\cf4 )\
    tco_date = st.date_input(\cf6 "TCO Date"\cf4 , \cf8 format\cf4 =\cf6 "%m/%d/%Y"\cf4 )\
    ops_walk_date = st.date_input(\cf6 "Ops Walk Date"\cf4 , \cf8 format\cf4 =\cf6 "%m/%d/%Y"\cf4 )\
    turnover_date = st.date_input(\cf6 "Turnover Date"\cf4 , \cf8 format\cf4 =\cf6 "%m/%d/%Y"\cf4 )\
    open_to_train_date = st.date_input(\cf6 "Open to Train Date"\cf4 , \cf8 format\cf4 =\cf6 "%m/%d/%Y"\cf4 )\
    store_opening = st.date_input(\cf6 "Store Opening"\cf4 , \cf8 format\cf4 =\cf6 "%m/%d/%Y"\cf4 )\
\
    notes = st.text_area(\cf6 "Notes (Use bullets or dashes)"\cf4 , \cf8 value\cf4 =\cf6 "\'95 "\cf4 , \cf8 height\cf4 =\cf10 200\cf4 )\
\
    submitted = st.form_submit_button(\cf6 "Submit"\cf4 )\
    \cf2 if \cf4 submitted:\
        data = \{\
            \cf6 "Store Name"\cf4 : store_name,\
            \cf6 "Store Number"\cf4 : store_number,\
            \cf6 "Subject"\cf4 : subject,\
            \cf6 "TCO Date"\cf4 : tco_date,\
            \cf6 "Ops Walk Date"\cf4 : ops_walk_date,\
            \cf6 "Turnover Date"\cf4 : turnover_date,\
            \cf6 "Open to Train Date"\cf4 : open_to_train_date,\
            \cf6 "Store Opening"\cf4 : store_opening,\
            \cf6 "Notes"\cf4 : notes\
        \}\
        data.update(types)\
        save_to_excel(data)\
        st.success(\cf6 "
\f1 \uc0\u9989 
\f0  Entry saved successfully!"\cf4 )\
\
st.subheader(\cf6 "
\f1 \uc0\u55357 \u56592 
\f0  Generate Weekly Report"\cf4 )\
report_pw = st.text_input(\cf6 "Enter Password to Generate Report"\cf4 , \cf8 type\cf4 =\cf6 "password"\cf4 )\
\cf2 if \cf4 st.button(\cf6 "Generate Report"\cf4 ):\
    df, html = generate_weekly_summary(report_pw)\
    \cf2 if \cf4 df \cf2 is not None\cf4 :\
        path = save_html_report(html)\
        st.success(\cf6 f"
\f1 \uc0\u9989 
\f0  Report generated and saved to: \cf2 \{\cf4 path\cf2 \}\cf6 "\cf4 )\
        st.download_button(\cf6 "Download Report"\cf4 , html, \cf8 file_name\cf4 =get_weekly_filename(), \cf8 mime\cf4 =\cf6 "text/html"\cf4 )\
    \cf2 else\cf4 :\
        st.error(html)\
\
}