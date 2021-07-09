from selenium.webdriver.support.ui import Select
from cryptography.fernet import Fernet
from datetime import datetime, timedelta
from selenium import webdriver
from bs4 import BeautifulSoup
from cs50 import SQL
import time
import re
import os


def find_click(element_id):
    variable = browser.find_element_by_id(element_id)
    variable.click()


def fill_out(element_id, data):
    variable = browser.find_element_by_id(element_id)
    variable.send_keys(data)


def drop_down_selection(element_id, selection):
    variable = browser.find_element_by_id(element_id)
    var = Select(variable)
    var.select_by_visible_text(selection)


# INITIATE A NEW APPLICATION
def new_efiling():
    find_click("disclamer")
    find_click("NewEfiling")


# STEP 1
def step_one(appeal_type):
    # CHOOSE ENGLISH AS LANGUAGE
    drop_down_selection("proceedingLang", "English")

    # CHOOSE IMMIGRATION AS PROCEEDING TYPE
    drop_down_selection("proceedingType", "Immigration")

    # CHOOSE PROCEEDING SUBJECT BASED ON THE USER INPUT
    proceeding_subject = browser.find_element_by_id("proceedingSubject")
    if appeal_type == "RPD" or appeal_type == "RAD" or appeal_type == "PRRA":
        refugee = Select(proceeding_subject)
        refugee.select_by_visible_text("Refugee")
        proceeding_nature = browser.find_element_by_id("proceedingNature")
        negative_decision = Select(proceeding_nature)
        if appeal_type == "RAD":
            negative_decision.select_by_visible_text(
                "Imm - Appl. for leave & jud. review - IRB - Refugee Appeal Division")
        elif appeal_type == "RPD":
            negative_decision.select_by_visible_text(
                "Imm - Appl. for leave & jud. review - IRB - Refugee Protection Div.")
        else:
            negative_decision.select_by_visible_text(
                "Imm - Appl. for leave & jud. review - Pre-removal risk assessment")
    elif appeal_type == "SP" or appeal_type == "TRV":
        non_refugee = Select(proceeding_subject)
        non_refugee.select_by_visible_text("Non-Refugee")
        proceeding_nature = browser.find_element_by_id("proceedingNature")
        negative_decision = Select(proceeding_nature)
        negative_decision.select_by_visible_text(
            "Imm - Appl. for leave & jud. review - Arising outside Canada")
    elif appeal_type == "H&C" or appeal_type == "Deferral":
        other = Select(proceeding_subject)
        other.select_by_visible_text("Non-Refugee")
        proceeding_nature = browser.find_element_by_id("proceedingNature")
        negative_decision = Select(proceeding_nature)
        negative_decision.select_by_visible_text(
            "Imm - Appl. for leave & jud. review - Other Arising in Canada")

    # CHOOSE THE DECISION MAKER BASED ON THE TYPE OF APPLICATION WE ARE APPEALING
    decision_maker = browser.find_element_by_id("DecisionMaker")
    irb = Select(decision_maker)

    if appeal_type == appeal_type == "H&C" or appeal_type == "SP" or appeal_type == "TRV":
        irb.select_by_visible_text("Citizenship and Immigration Canada")

    elif appeal_type == "RAD" or appeal_type == "RPD":
        irb.select_by_visible_text("Immigration and Refugee Board")

    elif appeal_type == "PRRA" or appeal_type == "Deferral":
        irb.select_by_visible_text("Canada Border Services Agency")

    find_click("Submit-Step-1")


# STEP 2
def step_two(number_of_applicants, first_names, last_names, appeal_type):
    find_click("addrow_Party")

    # CHOOSE THE PARTY ROLE AS APPLICANT
    party_role = browser.find_element_by_id("PartyRole_0")
    party_role.click()
    applicant = Select(party_role)
    applicant.select_by_visible_text("Applicant")

    # CHOOSE INDIVIDUAL
    drop_down_selection("PartyType_0", "Individual")

    # PUT FULL NAMES BASED ON THE NUMBER OF APPLICANTS
    fill_out("firstName_0", first_names[0])
    fill_out("lastName_0", last_names[0])

    # CLICK ADD PARTY BUTTON
    for x in range(number_of_applicants):
        find_click("addrow_Party")

    if number_of_applicants > 1:
        for x in range(1, number_of_applicants):
            party_role_others = browser.find_element_by_id(
                f"PartyRole_{x}")
            party_role_others.click()
            applicant_others = Select(party_role_others)
            applicant_others.select_by_visible_text("Applicant")
            party_details_others = browser.find_element_by_id(
                f"PartyType_{x}")
            party_details_others.click()
            individual_others = Select(party_details_others)
            individual_others.select_by_visible_text("Individual")
            fill_out(f"firstName_{x}", first_names[x])
            fill_out(f"lastName_{x}", last_names[x])
        multiple_doj = browser.find_element_by_id(
            f"PartyRole_{number_of_applicants}")
        multiple_doj.click()
        multiple_respondent = Select(multiple_doj)
        multiple_respondent.select_by_visible_text("Respondent (application)")
        doj_multiple_party_details = browser.find_element_by_id(
            f"PartyType_{number_of_applicants}")
        other_multiple = Select(doj_multiple_party_details)
        other_multiple.select_by_visible_text("Other")
        if appeal_type == "Deferral":
            fill_out(f"firstName_{number_of_applicants}",
                     "The Minister of Public Safety and Emergency Preparedness")
        else:
            fill_out(f"firstName_{number_of_applicants}",
                     "The Minister of Citizenship and Immigration")
    else:
        # ADD THE MINISTER / DOJ
        drop_down_selection("PartyRole_1", "Respondent (application)")
        drop_down_selection("PartyType_1", "Other")
        if appeal_type == "Deferral":
            fill_out(
                "firstName_1", "The Minister of Public Safety and Emergency Preparedness")
        fill_out("firstName_1", "The Minister of Citizenship and Immigration")
    find_click("Submit-Step-2")


# STEP 3
def step_three(number_of_applicants, file_path):
    # ADD DOCUMENT
    find_click("addrow")

    # SELECT THE DOCUMENT TYPE
    drop_down_selection(
        "DocumentType_0", "IMM - APPLICATION FOR LEAVE AND JUDICIAL REVIEW")

    # SELECT THE DOCUMENT LANGUAGE
    drop_down_selection("DocumentLanguage_0", "English")

    # CHECK ALL THE BOXES
    for x in range(number_of_applicants + 1):
        find_click(f"filer_0_{x}")

    # ATTACH THE DOCUMENT
    upload_document = browser.find_element_by_id("file_0")
    try:
        upload_document.send_keys(file_path)
        time.sleep(2)
    except Exception as e:
        print(str(e))
        print("Cannot find the document")

    find_click("Submit-Step-3")


# STEP 4
def step_four(results, appeal_type, sec_email):
    # FILING INFORMATION
    fill_out("firstName", results[0])
    fill_out("lastName", results[1])
    fill_out("Address", results[2])
    fill_out("City", results[3])
    drop_down_selection("provinceDDL", results[4])
    fill_out("postalCode", results[5])
    fill_out("phoneNumber", results[6])
    fill_out("priEmail", results[7])
    fill_out("secEmail", sec_email)
    drop_down_selection("languageDDL", results[8])
    drop_down_selection("regOfficeDDL", results[9])

    if appeal_type == "Deferral":
        find_click("isUrgent")
        textarea = browser.find_element_by_id("urgDesc")
        textarea.send_keys(".")

    find_click("Submit-Step-4")
    time.sleep(1.5)

    # SUBMIT
    # find_click("idMyBtn")
    # time.sleep(2)

    page = BeautifulSoup(browser.page_source, "html.parser")

    try:
        containers = page.findAll("div", {"class": "box"})
        html_text = containers[0].getText()
        confirmation_number = re.findall("[a-zA-Z]+-\d+-\S+", html_text)
    except Exception as e:
        confirmation_number = "Null"
        print("Problem with parsing the HTML", e)

    return confirmation_number


def efile_jr_notice(number_of_applicants, first_names, last_names,
                    appeal_type, results, file_path, secondary_email, user_id, key, folder_path):

    t1 = time.time()
    global browser
    browser = webdriver.Chrome()
    browser.get("https://efiling.fct-cf.gc.ca/en/online-access/e-filing-intro")
    browser.implicitly_wait(15)

    try:
        new_efiling()
    except Exception as e:
        print("Problem with the initial step", e)

    try:
        step_one(appeal_type)
    except Exception as e:
        print("Problem with the first step", e)

    try:
        step_two(number_of_applicants, first_names, last_names, appeal_type)
    except Exception as e:
        print("Problem with the second step", e)

    try:
        step_three(number_of_applicants, file_path)
    except Exception as e:
        print("Problem with the third step", e)

    try:
        confirmation_number = step_four(results, appeal_type, secondary_email)
    except Exception as e:
        print("Problem with the fourth step", e)

    # time.sleep(5)
    browser.quit()

    confirmation_number = "Null"
    if not secondary_email:
        secondary_email = "Null"

    dt1 = datetime.now()
    submission_date = dt1.strftime("%A-%B %d, %Y")

    dt2 = dt1 + timedelta(days=30)
    due_date = dt2.strftime("%A-%B %d, %Y")

    # IF THE DUE DATE FALLS IN THE WEEKEND, PUSH IT TO MONDAY
    if due_date.startswith("Saturday"):
        dt2 = datetime.now() + timedelta(days=32)
        due_date = dt2.strftime("%A-%B %d, %Y")
    elif due_date.startswith("Sunday"):
        dt2 = datetime.now() + timedelta(days=31)
        due_date = dt2.strftime("%A-%B %d, %Y")

    try:
        db = SQL("sqlite:///leave_app.db")
        f = Fernet(key)

        container = [last_names[0], first_names[0], appeal_type,
                     submission_date, due_date, secondary_email, confirmation_number]

        def encrypt(x):
            a = f.encrypt(x.encode())
            return a.decode()

        # encrypt the client information
        encrypted_container = list(map(encrypt, container))

        db.execute("INSERT INTO submissions (user_id, lastname, firstname, appeal_type,\
         submission_date, due_date, secondary_email,\
          confirmation_number) VALUES (?,?,?,?,?,?,?,?)", user_id, encrypted_container[0], encrypted_container[1],
                   encrypted_container[2], encrypted_container[3],
                   encrypted_container[4], encrypted_container[5],
                   encrypted_container[6])

        t2 = time.time()
        time_took = round(t2-t1, 3)
        db.execute("INSERT INTO meta VALUES (?,?,?)",
                   "jr_notice", str(dt1), time_took)

    except Exception as e:
        print("Problem with writing to the database", e)

    os.remove(file_path)
    # os.removedirs(folder_path)
