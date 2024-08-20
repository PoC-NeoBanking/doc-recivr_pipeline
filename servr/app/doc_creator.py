from fpdf import FPDF
import lorem

import random
import os
from datetime import datetime, timedelta
import argparse


DOCS_AMOUNT = 1 # Default amount of needed PDFs


PHRASE_NUMBER = 20 # Amount of human-written important phrases
FONTS = [
    "Times",
    "Arial",
    "Courier",
    "Helvetica"
     ]


def generate_legislation_phrase(used_phrases: set, control_set: set) -> str:
    if used_phrases == control_set:
        return lorem.paragraph()
    else:
        while True:
            n = round(random.uniform(0.5, 10.0), 2)
            n_days = int(n * 3)
            n_dollars = int(n * 10000)
            choise = random.randint(1, PHRASE_NUMBER)
            if choise not in used_phrases:
                phrases = {
                    1: f"Credit percentage is going to rise by {n} percent.",
                    2: f"The interest rate will be adjusted by {n} percent.",
                    3: f"Inflation rate is projected to increase by {n} percent.",
                    4: f"The loan term will be extended by {n} years.",
                    5: f"Mortgage rates will decrease by {n} percent next quarter.",
                    6: f"The deposit interest rate will increase by {n} percent.",
                    7: f"Transaction fees will be reduced by {n} percent for online banking.",
                    8: f"Savings account interest rates will be adjusted by {n} percent.",
                    9: f"New credit policies will lower the interest rate by {n} percent.",
                    10: f"The maximum credit limit will be raised by {n_dollars} dollars.",
                    11: f"Deposit insurance coverage will be extended by {n_dollars} dollars.",
                    12: f"Bank transfer fees will be waived for amounts exceeding {n_dollars} dollars.",
                    13: f"Overdraft protection limit will be increased by {n_dollars} dollars.",
                    14: f"Annual fees for credit cards will decrease by {n} percent.",
                    15: f"Fixed deposit interest rates will increase by {n} percent.",
                    16: f"Personal loan interest rates will be lowered by {n} percent.",
                    17: f"Online transaction limits will be increased by {n} percent.",
                    18: f"Cashback rates on purchases will rise by {n} percent.",
                    19: f"ATM withdrawal limits will be increased by {n_dollars} dollars.",
                    20: f"New banking regulations will reduce processing times by {n_days} days."
                }
                phrase = phrases[choise]
                used_phrases.add(choise)
                return phrase


def create_pdf(offset_amount: int) -> None:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font(random.choice(FONTS), size=random.randint(11, 13)) # Font formatting is different for different docs
    
    used_phrases, control_set = set(),  set()
    for i in range(1, PHRASE_NUMBER + 1):
        control_set.add(i)
    
    consecutive_phrase_counter = 0
    for _ in range(30):
        # 30% chance to add a legislation phrase, phrase will not be added more than two times in a row
        if random.random() <= 0.3 and consecutive_phrase_counter < 2:  
            text = generate_legislation_phrase(used_phrases, control_set)
            consecutive_phrase_counter += 1
        else:
            text = lorem.paragraph()

            consecutive_phrase_counter = 0

        match random.randint(1, 3): # Additional formatting randomness
            case 1:
                pdf.multi_cell(0, 10, text)
                pdf.ln(10)
            case 2:
                pdf.multi_cell(0, 10, text)
                text = lorem.paragraph()
                pdf.multi_cell(0, 10, text)

                consecutive_phrase_counter = 0
            case 3:
                pdf.multi_cell(0, 10, text)
    
    if not os.path.exists("./docs"):
        os.makedirs("./docs")
    
    current_time = datetime.now()
    # Changing creation time of docs so in case of multiple docs created name would not be same
    offset_time = current_time + timedelta(seconds=offset_amount)
    timestamp = offset_time.strftime("%Y%m%d%H%M%S")
    file_name = f"docs/{timestamp}.pdf"
    
    pdf.output(file_name)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Creates a PDF legislation mock-up.", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-a', '--amount', type=int, default=DOCS_AMOUNT, help='amount of docs needed from script (default: 1)\ntime of document creation will be offset for <a> seconds from the script start')
    args = parser.parse_args()

    for n in range(0, args.amount):
        create_pdf(n)