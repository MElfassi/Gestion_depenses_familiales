from email.policy import default

import streamlit as st
import sqlite3
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
from requests import delete


# Classe pour la gestion de la base de données
class Database:
    def __init__(self, db_name="expenses.db"):
        """Initialise la connexion à la base de données SQLite."""
        self.conn = sqlite3.connect(db_name)
        self.create_tables()

    def create_tables(self):
        """Crée les tables nécessaires pour les dépenses, les catégories, et les montants initiaux."""
        with self.conn:
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL
                )
            ''')
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    amount REAL NOT NULL,
                    date TEXT NOT NULL,
                    category_id INTEGER,
                    FOREIGN KEY (category_id) REFERENCES categories(id)
                )
            ''')
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS starting_amounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    amount REAL NOT NULL,
                    date TEXT NOT NULL
                )
            ''')

    def add_category(self, name):
        """Ajoute une nouvelle catégorie de dépenses."""
        with self.conn:
            self.conn.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (name,))

    def add_expense(self, amount, date, category_id):
        """Enregistre une nouvelle dépense."""
        with self.conn:
            self.conn.execute(
                "INSERT INTO expenses (amount, date, category_id) VALUES (?, ?, ?)",
                (amount, date, category_id)
            )

    def add_amount(self, amount, date):
        """Ajoute un montant de départ avec une date."""
        with self.conn:
            self.conn.execute("INSERT INTO starting_amounts (amount, date) VALUES (?, ?)", (amount, date))

    def get_categories(self):
        """Récupère toutes les catégories de dépenses."""
        return self.conn.execute("SELECT * FROM categories").fetchall()

    def get_expenses(self):
        """Récupère toutes les dépenses enregistrées."""
        return self.conn.execute("SELECT * FROM expenses order by date").fetchall()


    def get_starting_amounts(self):
        """Récupère les montants de départ et leurs dates."""
        return self.conn.execute("SELECT * FROM starting_amounts ORDER BY date").fetchall()

    def get_total_expenses(self):
        """Calcule le total des dépenses."""
        return self.conn.execute("SELECT SUM(amount) FROM expenses").fetchone()[0] or 0
    def expenses_time(self):
        """Calcul le montant de dépenses par jour"""
        return self.conn.execute("select date, sum(amount) from expenses group by date")
    def get_total_amount(self):
        return self.conn.execute("select * from starting_amounts")

# Classe principale pour l'application
class Amount_Manager:
    def __init__(self):
        """Initialise la classe de gestion des dépenses."""
        self.db = Database()

    def set_amount(self):
        """Permet de définir le montant de départ."""
        amount = st.number_input("Montant à ajouter:", min_value=0.0, step=10.0)
        date = st.date_input("Indiquer la date de disponibilité de l'argent")
        if st.button("Définir le nouveau montant"):
            if amount >0:
                if date == '':
                    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.db.add_amount(amount, date)
                st.success(f"Montant de départ de {amount} € ajouté le {date}")
            else:
                st.write(f"## Le montant doit être supérieur à 0")


    def add_category(self):
        """Ajoute une nouvelle catégorie de dépenses."""
        category_name = st.text_input("Nom de la catégorie:")
        if st.button("Ajouter la catégorie"):
            if category_name:
                self.db.add_category(category_name)
                st.success(f"Catégorie '{category_name}' est ajoutée")
            else:
                st.write(f"## Voulez-vous vraiment ajouter une catégorie sans nom !!!!")

    def get_category(self):
        """Liste des category de dépenses et donne la possibilité de supprimer une."""

        # Supprime la catégorie en dehors de la boucle
        selected_categories = st.multiselect(" *:red[Sélectionnez les catégories à supprimer]*",
                                             [  l[1] for l in self.db.get_categories()])
        if selected_categories:
            st.write(" #### Tu as choisi de supprimer le ou les categories suivantes: ", selected_categories)
            if st.button(" Supprimer les catégories sélectionnées",icon="🔥"):
                with self.db.conn:
                    for category_name in selected_categories:
                        # Récupère l'id de la catégorie
                        category_id = [l[0] for l in self.db.get_categories() if l[1] == category_name][0]

                        # Supprime la catégorie par id
                        self.db.conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))

                st.success("Catégories supprimées avec succès.")

        # Récupère et affiche les catégories après suppression éventuelle
        list_category = self.db.get_categories()
        st.write(f"### *Voici votre liste des catégories*: ")
        for l_cat in list_category:
            st.write(f"Catégorie {l_cat[1]} ")

    def add_expense(self):
        """Ajoute une dépense en indiquant le montant, la date et la catégorie."""
        amount = st.number_input("Montant de la dépense:", min_value=0.0, step=1.0)
        date = st.date_input("Date de la dépense:")
        categories = self.db.get_categories()
        category = st.selectbox("Catégorie:", [cat[1] for cat in categories],index=None)

        if st.button("Ajouter la dépense"):
            if amount >0:
                if category:
                    category_id = [cat[0] for cat in categories if cat[1] == category][0]
                    self.db.add_expense(amount, date.strftime("%Y-%m-%d"), category_id)
                    st.success(f"Dépense de {amount} € ajoutée pour la catégorie '{category}' le {date}")
                else:
                    st.write(f"### :red[Veuillez sélectionner une categorie de dépense !!]")
            else:
                st.write(f"## :red[Veuillez mettre un montant supérieur à zéro !!]")

    def show_expenses(self):
        """Affiche toutes les dépenses sous forme de tableau avec la possibilité de les modifier ou de les supprimer."""
        expenses = self.db.get_expenses()
        amountss = self.db.get_starting_amounts()
        categories = {cat[0]: cat[1] for cat in self.db.get_categories()}
        st.write("##### Liste des dépenses")
        for expense in expenses:
            st.write(f"Montant: {expense[1]} €, Date: {expense[2]}, Catégorie: {categories.get(expense[3], 'N/A')}")
            if st.button(f"Supprimer {expense[1]} € du {expense[2]}", key=expense[0]):
                with self.db.conn:
                    self.db.conn.execute("DELETE FROM expenses WHERE id = ?", (expense[0],))
                    st.success("Dépense supprimée")
        st.write("##### Liste des sommes ajoutés")
        for amoun in amountss:
            st.write(f"Somme  de {amoun[1]} € ajouté le {amoun[2]}")
            if st.button(f"Supprimer {amoun[1]} € du {amoun[2]}", key=amoun[0]):
                with self.db.conn:
                    self.db.conn.execute("DELETE FROM starting_amounts WHERE id = ?", (amoun[0],))
                    st.success("Ajout supprimé")

    def show_balance(self):
        """Calcule et affiche le montant restant à dépenser."""
        starting_amounts = self.db.get_starting_amounts()
        if starting_amounts:
            total_starting = sum(amount[1] for amount in starting_amounts)
            if total_starting:
                total_expenses = self.db.get_total_expenses()
                remaining_balance = total_starting - total_expenses
                if remaining_balance > 500:
                    st.write(f" ###  Reste à dépenser: :green[*{remaining_balance}*] €")
                elif 500 > remaining_balance > 100:
                    st.write(f" ###  Reste à dépenser: :orange[*{remaining_balance}*] €")
                else:
                    st.write(f" ###  Reste à dépenser: :red[*{remaining_balance}*] €")
            else:
                st.write(f"## Avez vous insérez des *montants* ou des *dépenses* ? :money_with_wings:")

    def liste_ajout(self):
        liste_ajouts = self.db.get_total_amount()
        for lis in liste_ajouts:
            st.write(f"voici les ajouts lis[0] et lis[1] et lis[2] ")


# Lancer l'application Streamlit
def main():
    st.title("Application de gestion des dépenses")

    manager = Amount_Manager()

    st.sidebar.header("Options")
    choice = st.sidebar.selectbox("Choisissez une option",
                                  ["Définir le montant à ajouter", "Ajouter une catégorie", "Liste des Categories",
                                   "Ajouter une dépense", "Voir les dépenses", "Voir le solde","Total Ajout"])

    if choice == "Définir le montant à ajouter":
        manager.set_amount()
    if choice == "Ajouter une catégorie":
        manager.add_category()
    if choice == "Liste des Categories":
        manager.get_category()
    if choice == "Ajouter une dépense":
        manager.add_expense()
    if choice == "Voir les dépenses":
        # st.write(f" ### Le solde")
        # manager.show_balance()
        st.write(" ### La liste des ajouts et Dépenses")
        manager.show_expenses()
    if choice == "Voir le solde":
        manager.show_balance()
    if choice == "Total Ajout":
        manager.liste_ajout()


if __name__ == "__main__":
    main()
