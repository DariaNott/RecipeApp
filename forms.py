from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, SelectField, FloatField, FieldList, FormField, SelectMultipleField
from wtforms.validators import DataRequired, Length, NumberRange


class IngredientForm(FlaskForm):
    # Примітка: title має бути фактично ID існуючого інгредієнта,
    # але для простоти прикладу використовуємо StringField.
    # У реальному застосунку це буде SelectField або розширений пошук.
    title = SelectField('Назва інгредієнта', validators=[DataRequired(), Length(max=100)])
    amount = FloatField('Кількість', validators=[DataRequired(), NumberRange(min=0.01)])
    measure = StringField('Міра (грам, шт., ст.л.)', validators=[DataRequired(), Length(max=20)])


class RecipeForm(FlaskForm):
    title = StringField('Назва рецепта', validators=[DataRequired(), Length(max=255)])
    instructions = TextAreaField('Інструкція приготування', validators=[DataRequired()])

    categories = SelectMultipleField(
        'Категорії',
        coerce=int,
        validators=[DataRequired()]
    )

    def set_categories_choices(self, category_choices):
        self.categories.choices = category_choices

    submit = SubmitField('Зберегти рецепт')