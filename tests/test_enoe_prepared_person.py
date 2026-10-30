import psycopg
import pytest

from platform_work_reform.enoe_staging import ARCHIVE_SHA256

pytestmark = pytest.mark.integration

HEADER = (
    "r_def,cve_loc,cve_mun,est,est_d_tri,est_d_men,cve_ageb,t_loc_tri,t_loc_men,cd_a,"
    "cve_ent,con,upm,d_sem,n_pro_viv,v_sel,n_hog,h_mud,n_ent,per,n_ren,c_res,par_c,sex,"
    "eda,nac_dia,nac_mes,nac_anio,l_nac_c,cs_p12,cs_p13_1,cs_p13_2,cs_p14_c,cs_p15,"
    "cs_p16,cs_p17,n_hij,e_con,cs_p20a_1,cs_p20a_c,cs_p20b_1,cs_p20b_c,cs_p20c_1,"
    "cs_ad_mot,cs_p21_des,cs_ad_des,cs_nr_mot,cs_p23_des,cs_nr_ori,ur,zona,salario,"
    "fac_tri,fac_men,clase1,clase2,clase3,pos_ocu,seg_soc,rama,c_ocu11c,ing7c,dur9c,"
    "emple7c,medica5c,buscar5c,rama_est1,rama_est2,dur_est,ambito1,ambito2,tue1,tue2,"
    "tue3,busqueda,d_ant_lab,d_cexp_est,dur_des,sub_o,s_clasifi,remune2c,pre_asa,"
    "tip_con,dispo,nodispo,c_inac5c,pnea_est,niv_ins,eda5c,eda7c,eda12c,eda19c,hij5c,"
    "domestico,anios_esc,hrsocup,ingocup,ing_x_hrs,tpg_p8a,tcco,cp_anoc,imssissste,"
    "ma48me1sm,p14apoyos,scian,t_tra,emp_ppal,tue_ppal,trans_ppal,mh_fil2,mh_col,"
    "sec_ins,tipo,mes_cal,cvegeo"
).split(",")


def test_prepared_universe_invalid_and_source_boundary(isolated_database):
    with psycopg.connect(**isolated_database.connection_parameters()) as conn:
        source = conn.execute(
            """INSERT INTO meta.source_file(source_name,original_name,sha256,byte_size)
               VALUES ('enoe','pilot.zip',%s,1) RETURNING id""",
            (ARCHIVE_SHA256,),
        ).fetchone()[0]
        run = conn.execute(
            """INSERT INTO meta.ingestion_run(source_file_id,status,finished_at)
               VALUES (%s,'succeeded',now()) RETURNING id""",
            (source,),
        ).fetchone()[0]
        conn.execute(
            """INSERT INTO staging.enoe_load VALUES
               (%s,%s,'2025-07-01','enoe-2025q3-v1')""",
            (run, source),
        )
        conn.execute(
            """INSERT INTO staging.enoe_table VALUES (%s,'SDEM',%s,6,%s,%s)""",
            (run, HEADER, "a" * 64, "b" * 64),
        )
        for number, age, weight in [
            (1, "30", "10"),
            (2, "98", "5"),
            (3, "99", "5"),
            (4, "", "5"),
            (5, "30", "x"),
            (6, "14", ""),
        ]:
            fields = dict.fromkeys(HEADER, "") | {
                "r_def": "0",
                "c_res": "1",
                "eda": age,
                "fac_tri": weight,
                "clase1": "1",
                "clase2": "1",
            }
            conn.execute(
                "INSERT INTO staging.enoe_row VALUES (%s,'SDEM',%s,%s,%s)",
                (
                    run,
                    number,
                    ["01"] * 8 + [str(number)],
                    [fields[name].encode() for name in HEADER],
                ),
            )
        conn.execute(
            "INSERT INTO staging.enoe_row VALUES (%s,'SDEM',7,%s,%s)",
            (run, ["01"] * 8 + ["7"], [b"0"]),
        )
        rows = conn.execute(
            """SELECT preparation_status, quarterly_weight, coe1_row_number
               FROM enoe.prepared_person_2025q3_v1 ORDER BY sdem_row_number"""
        ).fetchall()
        assert rows == [
            ("eligible", 10, None),
            ("eligible", 5, None),
            ("outside_universe", None, None),
            ("invalid", None, None),
            ("invalid", None, None),
            ("outside_universe", None, None),
            ("invalid", None, None),
        ]
        conn.execute("UPDATE staging.enoe_table SET header[1]='changed' WHERE run_id=%s", (run,))
        assert conn.execute("SELECT count(*) FROM enoe.prepared_person_2025q3_v1").fetchone() == (
            0,
        )
