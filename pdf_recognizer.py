from pdfminer.high_level import extract_text


class PdfRecognizer:
    def __init__(self, filename):
        self.applicant_names = ()
        self.applicant_lastnames = ()
        self.number_of_applicants = None
        self.file = filename
        self.ledger = {"number_of_applicants": None,
                       "app_fullname": None}

    def extract_fullnames(self):
        try:
            # EXTRACT THE TEXT OUT OF THE PDF FILE
            text = extract_text(self.file, page_numbers=[0])

            # GET THE SECTION WE WANT - THE UPPER PART
            section = text.split(" and")[0]
            chunks = set(section.split('\n'))
            # print(chunks)

            chunks_stripped = set(map(lambda x: x.strip(), chunks))

            # DEFINE THE WORDS THAT YOU WANT TO REMOVE
            redundants = {
                "Registry",
                "FEDERAL",
                "FEDERAL COURT",
                "Registry No: IMM-",
                "B E T W E E N",
                "B E T W E E N :",
                "Applicant",
                "Applicants",
                "BETWEEN",
                "Between",
                "Court",
                "MINISTER",
                "-",
                ""
            }

            difference = chunks_stripped.difference(redundants)

            # print(f"\n{len(difference)} Applicant(s) in total.\n")
            self.number_of_applicants = len(difference)
            self.ledger["number_of_applicants"] = len(difference)

            self.applicant_lastnames = (applicant.split(
                " ")[-1] for applicant in difference)

            self.applicant_names = (" ".join(applicant.split(
                " ")[:-1]) for applicant in difference)

            self.ledger["app_fullname"] = tuple(
                zip(self.applicant_names, self.applicant_lastnames))

        except:
            print(
                "\nEither there is no file in the directory OR I can not recognize text in the file.\n")


# pdf = PdfRecognizer("./static/pdf/App.pdf")
# pdf.extract_fullnames()
# print(pdf.ledger)
