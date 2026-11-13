# Allergies

A customer wrote in about her peanut allergy, quite upset. She has "Peanuts" in her profile, and still, typing
"chi" in the search box offered her "Chicken satay skewers" and "Chicken curry", and her dinner plan had the satay
skewers on day six. The skewers are made with our satay sauce, and the curry is cooked in groundnut oil.

Allergy handling in the app feels half-finished in general, so please give it some love: make it more solid and
tidy up what you find. It would also be good if people could somehow tell that recipes are being left out for them;
I'll leave it to you how.

The one thing that has to hold: `search`, `suggest`, `plan_week` and `similar` (all from `mealplan`) never show a
customer a recipe that contains something in their profile's `allergens`. A recipe contains an allergen when

- one of its ingredients is that allergen or contains it, under any name our ingredient table
  (`mealplan/ingredients.py`) knows it by: groundnut oil is peanut oil, which contains peanut; butter contains milk;
- or a recipe it uses as a component contains it, at any depth: the party platter uses the skewers, which use the
  satay sauce.

Customers type allergens however they like ("Peanuts", "groundnut", "Dairy"); the ingredient table knows those
names too.

Everything else stays as it is. A customer with no allergens sees exactly what they see today from all four. For
anyone else, the recipes that are left come in the same order as today; `suggest` and `similar` still give up to
`limit` results when that many are left to give; and the plan still has a dinner for every day, chosen the same way
as today from the dinners that are left. The four functions keep their parameters and return what they return now.
