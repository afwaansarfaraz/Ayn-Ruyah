import sqlite3

def cleanup():
    conn = sqlite3.connect("data/retinalens.db")
    c = conn.cursor()

    # Find genuine duplicate patient registrations by matching tenant, name, DOB and phone
    c.execute("""
        SELECT tenant_id, first_name, last_name, dob, phone, count(*) 
        FROM patients 
        GROUP BY tenant_id, first_name, last_name, dob, phone 
        HAVING count(*) > 1
    """)
    dups = c.fetchall()
    for tenant_id, first_name, last_name, dob, phone, count in dups:
        c.execute("""
            SELECT id, created_at FROM patients 
            WHERE tenant_id = ? AND first_name = ? AND last_name = ? AND dob = ? AND phone = ?
            ORDER BY created_at ASC
        """, (tenant_id, first_name, last_name, dob, phone))
        records = c.fetchall()
        primary_id = records[0][0]
        duplicate_ids = [r[0] for r in records[1:]]
        print(f"Keeping primary {first_name} {last_name}: {primary_id}, removing {len(duplicate_ids)} duplicates")
        
        # Re-link any screenings to the primary patient
        for dup_id in duplicate_ids:
            c.execute("UPDATE screenings SET patient_id = ? WHERE patient_id = ?", (primary_id, dup_id))
            c.execute("DELETE FROM patients WHERE id = ?", (dup_id,))

    # Deduplicate repeated screenings only when they share a reliable event or import identifier
    c.execute("PRAGMA table_info(screenings)")
    cols = {r[1] for r in c.fetchall()}
    identifier_col = "import_id" if "import_id" in cols else ("event_id" if "event_id" in cols else None)

    if identifier_col:
        c.execute(f"""
            SELECT tenant_id, {identifier_col}, count(*) 
            FROM screenings 
            WHERE {identifier_col} IS NOT NULL AND {identifier_col} != ''
            GROUP BY tenant_id, {identifier_col} 
            HAVING count(*) > 1
        """)
        screening_dups = c.fetchall()
        for tenant_id, ident_val, count in screening_dups:
            c.execute(f"""
                SELECT id, created_at FROM screenings 
                WHERE tenant_id = ? AND {identifier_col} = ?
                ORDER BY created_at DESC
            """, (tenant_id, ident_val))
            records = c.fetchall()
            primary_screening_id = records[0][0]
            duplicate_screening_ids = [r[0] for r in records[1:]]
            print(f"Keeping primary screening {primary_screening_id} for {identifier_col}={ident_val}, removing {len(duplicate_screening_ids)} duplicate screenings")
            for dup_id in duplicate_screening_ids:
                c.execute("DELETE FROM screenings WHERE id = ?", (dup_id,))
    else:
        print("No event or import identifier column on screenings; preserving separate visits.")

    # Update any dicebear avatar URLs in patients table to neutral SVGs
    c.execute("SELECT id, gender, avatar_url FROM patients WHERE avatar_url LIKE '%dicebear%'")
    dicebear_rows = c.fetchall()
    print(f"Updating {len(dicebear_rows)} dicebear avatars in patients table")
    for pid, gender, _ in dicebear_rows:
        new_avatar = "/assets/branding/avatar_female.svg" if (gender or "").lower() == "female" else "/assets/branding/avatar_male.svg"
        c.execute("UPDATE patients SET avatar_url = ? WHERE id = ?", (new_avatar, pid))

    conn.commit()
    c.execute("SELECT count(*) FROM patients")
    print("Final patient count:", c.fetchone()[0])
    conn.close()

if __name__ == "__main__":
    cleanup()

