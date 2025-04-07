from sqlalchemy import Column, Integer, String, DECIMAL, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Pharmacies(Base):
    __tablename__ = 'pharmacies'
    id = Column(Integer, primary_key=True, index=True)
    
    name = Column(String, index=True)
    opening_day = Column(String, index=True)
    open_time = Column(String, index=True)
    close_time = Column(String, index=True)

    __table_args__ = (
        UniqueConstraint('name', 'opening_day', 'open_time', 'close_time', name='uix_pharmacy_openning'),
    )


class PharmaciesCash(Base):
    __tablename__ = 'pharmacies_cash'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    sold_item = Column(Integer, ForeignKey('pharmacies_mask.id'), nullable=True)
    cash_balance = Column(DECIMAL(10, 2), index=True)  

    __table_args__ = (
        UniqueConstraint('name', 'sold_item', 'cash_balance', name='uix_pharmacies_cash'),
    )
    
    
class PharmaciesMask(Base):
    __tablename__ = 'pharmacies_mask'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    mask_name = Column(String, index=True)
    mask_color = Column(String, index=True)
    pack_quantity = Column(Integer, index=True)
    price = Column(DECIMAL(10, 2), index=True)

    __table_args__ = (
        UniqueConstraint('name', 'mask_name', 'mask_color', 'pack_quantity', 'price', name='uix_pharmacies_mask'),
    )


class Users(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    cash_balance = Column(DECIMAL(10, 2), index=True)
    
    __table_args__ = (
        UniqueConstraint('name', 'cash_balance', name='uix_users'),
    )
    
    
class UsersPurchaseHistory(Base):
    __tablename__ = 'users_purchase_history'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True)
    pharmacies = Column(Integer, ForeignKey('pharmacies.id'), index=True)
    pharmacies_mask = Column(Integer, ForeignKey('pharmacies_mask.id'), index=True)
    trn_amount = Column(DECIMAL(10, 2))
    trn_date = Column(DateTime)

    __table_args__ = (
        UniqueConstraint('user_id', 'pharmacies', 'pharmacies_mask', 'trn_amount', 'trn_date', name='uix_users_purchase_history'),
    )
