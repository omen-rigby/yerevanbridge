import re

from wtforms import StringField, validators, SelectField, SubmitField, IntegerField
from flask_wtf import FlaskForm


class ResultForm(FlaskForm):
    city = SelectField('Select city', choices=[
        ('yerevan', 'Yerevan'),
        ('voronezh', 'Воронеж'),
        ('yessentuki', 'Ессентуки'),
        ('izhevsk', 'Ижевск'),
        ('kursk', 'Курск')
    ], validators=[validators.DataRequired()], name='city')
    board = IntegerField(label='Board', name='board', validators=[
        validators.data_required(), validators.number_range(1, 999)])
    contract = StringField(label='Contract', name='contract', description='3hxe or pass', validators=[
        validators.regexp(re.compile('(pass)|([1-7] *(([cdsh])|(nt?)) *x{0,2} *[news])', re.IGNORECASE))
    ])
    # lead_suit = SelectField(label='Lead, e.g. h4', name='lead_suit', choices=[
    #     ('c', 'c'), ('d', 'd'), ('h', 'h'), ('s', 's')])
    lead_card = StringField(label='Lead', description='Example: st', name='lead', validators=[
        validators.regexp(re.compile('([cdhs]([23456789tjqka]|(10)))|(([23456789tjqka]|(10))[cdhs])'), re.IGNORECASE)])
    _result_choices = [('m13', '-13'), ('m12', '-12'), ('m11', '-11'),
        ('m10', '-10'), ('m9', '-9'), ('m8', '-8'), ('m7', '-7'), ('m6', '-6'), ('m5', '-5'), ('m4', '-4'),
        ('m3', '-3'), ('m2', '-2'), ('m1', '-1'), ('made', '='), ('p1', '+1'), ('p2', '+2'), ('p3', '+3'),
        ('p4', '+4'),  ('p5', '+5'), ('p6', '+6')
    ]
    result = SelectField(label='Tricks', name='result', choices=[], default='made')
    submit = SubmitField('Submit')


