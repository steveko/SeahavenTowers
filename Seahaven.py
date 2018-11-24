import random
import math
import console

from itertools import product


# some constants to avoid using "magic" numbers
NUM_TOWERS = 10
NUM_CELLS = 4
NUM_SLOTS = 4
NUM_CARDS_PER_TOWER = 5


def is_descending_sequence_common_suit(cards):
	last_card = None
	for c in cards:
		if last_card:
			if c.suit != last_card.suit or c.rank != last_card.rank-1:
				return False
		last_card = c
	return True


class Card (object):
	'''
	suit is an integer from 0 to 3 (clubs=0, diamonds, hearts, spades=3)
	rank is an integer from 1 to 13 (ace=1, jack=11, queen=12, king=13)
	'''
	
	# some constants for making card creation easier to read
	
	# suits
	clubs = 0
	diamonds = 1
	hearts = 2
	spades = 3
	
	# ranks that aren't just numbers
	ace = 1
	jack = 11
	queen = 12
	king = 13
	
	all_suits = [clubs, diamonds, hearts, spades]
	all_ranks = [ace, 2, 3, 4, 5, 6, 7, 8, 9, 10, jack, queen, king]
	
	# for printf debugging purposes mostly
	suit_map = "♧♢♡♤"
	rank_map = ".A23456789TJQK"
	
	def __init__(self, rank, suit):
		self.rank = rank
		self.suit = suit
		
	def __repr__(self):
		return Card.rank_map[self.rank] + Card.suit_map[self.suit]
		
	def __eq__(self, other):
		return self.rank == other.rank and self.suit == other.suit
		
	def __hash__(self):
		return hash((self.rank, self.suit))


class Deck (object):
	def __init__(self):
		ranks = Card.all_ranks
		suits = Card.all_suits
		self.cards = [Card(r, s) for r, s in product(ranks, suits)]
			
	def shuffle(self):
		random.shuffle(self.cards)
		
	def deal(self, number):
		hand = self.cards[-number:]
		del self.cards[-number:]
		return hand
		
		
class Seahaven (object):
		
	def __init__(self):
		self.gui = None
		self.new_game()
		
	def new_game(self):
		deck = Deck()
		deck.shuffle()
		self.slots = []
		self.move_history = [] # list of (source slot index, dest slot index, count, is_auto) tuples
		self.redo_stack = []
		
		# slots at indices 0-9 are the towers
		for _ in range(NUM_TOWERS):
			self.slots.append(deck.deal(NUM_CARDS_PER_TOWER))
		
		# slots at indices 10-13 are the cells
		for _ in range(NUM_SLOTS):
			if len(deck.cards) > 0:
				self.slots.append(deck.deal(1))
			else:
				self.slots.append([])
		
		# slots at indices 14-17 are the suit slots
		for _ in range(NUM_CELLS):
			self.slots.append([])
			
		self.empty_cells_count = 2
		
		self.do_auto_moves(animate=False, record=False)
		
	def __repr__(self):
		s = "Towers:\n"
		
		for i in range(10):
			slot = self.slots[i]
			s += "{0}: {1!s}\n".format(i, slot)
			
		s += "\nCells:\n"
		for i in range(10, 14):
			slot = self.slots[i]
			s += "{0}: {1!s}\n".format(i, slot)
			
		s += "\nSuits:\n"
		for suit in Card.all_suits:
			i = self.slot_index_for_suit(suit)
			slot = self.slots[i]
			s += "{0}: {1!s}\n".format(Card.suit_map[suit], slot)
			
		return s
		
	def slot_for_tower(self, tower_index):
		return self.slots[tower_index]
		
	def slot_for_cell(self, i):
		return self.slots[10+i]
		
	def slot_for_suit(self, suit):
		return self.slots[self.slot_index_for_suit(suit)]
		
	def is_tower_slot(self, slot_index):
		return slot_index < 10
		
	def is_cell_slot(self, slot_index):
		return slot_index >= 10 and slot_index < 14
		
	def is_suit_slot(self, slot_index):
		return slot_index >= 14
		
	def is_valid_slot_index(self, slot_index):
		return slot_index >= 0 and slot_index < 18
		
	def slot_index_for_suit(self, suit):
		return suit+14
		
	def move(self, source, dest, count):
		'''
		source and dest are integers that identify a tower or free cell.
		0-9: tower slots
		10-13: free cell slots
		14-17: suit slots
		'''
		
		# Make sure this is a valid move. Short-circuit rest of function and return
		# False immediately if it is not a valid move.
		if count < 1:
			print("Invalid move: count < 1")
			return False
		if not self.is_valid_slot_index(source):
			print("Invalid move: source index out of range")
			return False
		if not self.is_valid_slot_index(dest):
			print("Invalid move: dest index out of range")
			return False
		if source == dest:
			print("Invalid move: source == dest")
			return False
		if count > len(self.slots[source]):
			print("Invalid move: not enough cards in source slot")
			return False
									
		cards_to_move = self.slots[source][-count:]
		first_move_card = cards_to_move[0]
		if self.is_cell_slot(dest): # destination is a cell...
			# ... destination must be empty
			if len(self.slots[dest]) > 0:
				print("Invalid move: destination is a cell and it is not empty")
				return False
			# ... count must be 1
			if count > 1:
				print("Invalid move: destination is a cell and count > 1")
				return False
		else: # destination is not a cell...
			if first_move_card.rank == Card.king: # ...first card is a King...
				# ...dest must be a empty
				if len(self.slots[dest]) > 0:
					print("Invalid move: first card being moved is King, but dest is not empty")
					return False
			else: # ...first card is not a King...
				# ...dest must NOT be empty
				if len(self.slots[dest]) == 0:
					print("Invalid move: first card being moved is not King, and dest is empty")
					return False
				last_dest_card = self.slots[dest][-1]
				# ... suits match
				if first_move_card.suit != last_dest_card.suit:
					print("Invalid move: first card being moved and last card of dest do not match suits")
					return False
				# ... ranks are descending
				if first_move_card.rank+1 != last_dest_card.rank:
					print("Invalid move: first card being moved of wrong rank")
					return False
					
			if count > 1:
				# source and dest must be towers
				if self.is_cell_slot(source) or self.is_cell_slot(dest):
					print("Invalid move: count > 1 and source (%d) or dest (%d) is a cell" % (source, dest))
					return False
				# there must be at least count-1 open free cells
				if count > self.empty_cells_count+1:
					print("Invalid move: trying to move %d cards when only %d cells are open" % (count, self.empty_cells_count))
					return False
				# all cards being moved must be of same suit and descending in rank sequentially
				if not is_descending_sequence_common_suit(cards_to_move):
					print("Invalid move: trying to move > 1 cards that are not in sequence: " + cards_to_move.__repr__())
					return False
								
		# if we get to here, then the move is valid, so move count cards from source to dest
		self.do_raw_move(source, dest, count, False, animate=True, record=True, clear_redo=True)
		self.do_auto_moves()
		
		return True
		
	def do_auto_moves(self, animate=True, record=True):
		made_move = True
		while made_move:
			made_move = False
			for suit in Card.all_suits:
				suit_slot_index = self.slot_index_for_suit(suit)
				suit_slot = self.slots[suit_slot_index]
				if len(suit_slot) == 0:
					target_rank = Card.ace
				else:
					target_rank = suit_slot[-1].rank + 1
				source = self.find_slot_with_card(Card(target_rank, suit))
				if source >= 0:
					self.do_raw_move(source, suit_slot_index, 1, True, animate, record)
					made_move = True
	
	def do_raw_move(self, source, dest, count, is_auto, animate=True, record=True, clear_redo=False):
		
		if animate and self.gui:
			source_cards = self.slots[source][-count:]
			if self.is_suit_slot(dest):
				dest_offset = 0
			else:
				dest_offset = len(self.slots[dest])
			self.gui.queue_animation(source_cards, dest, dest_offset)
		
		# if source is a cell, then increment free cell count
		if self.is_cell_slot(source):
			self.empty_cells_count += 1
			
		# if dest is a cell, then decrement free cell count
		if self.is_cell_slot(dest):
			self.empty_cells_count -= 1
			
		cards_to_move = self.slots[source][-count:]
		
		# actually move the cards from source to dest slot
		self.slots[dest].extend(cards_to_move)
		del self.slots[source][-count:]
		
		# record the move
		if record:
			move = (source, dest, count, is_auto)
			self.move_history.append(move)
			
		if clear_redo:
			self.redo_stack = []
	
	def find_slot_with_card(self, card):
		'''
		Search top cards of towers and cells for card with given rank and suit.
		If found, return the index of that slot. Otherwise, return -1.
		'''
		for i in range(14):
			slot = self.slots[i]
			if len(slot) > 0:
				top_card = slot[-1]
				if top_card == card:
					return i
		
		return -1

	def undo(self):
		while len(self.move_history) > 0:
			move = self.move_history.pop()
			self.redo_stack.append(move)
			(source, dest, count, is_auto) = move
			self.do_raw_move(dest, source, count, is_auto, animate=True, record=False)
			if not is_auto:
				break
		
	def redo(self):
		check_for_auto = False
		while len(self.redo_stack) > 0:
			move = self.redo_stack.pop()
			(source, dest, count, is_auto) = move
			if check_for_auto and not is_auto:
				self.redo_stack.append(move)
				break
			self.do_raw_move(source, dest, count, is_auto, animate=True, record=True, clear_redo=False)
			check_for_auto = True
		
	def has_undo(self):
		return len(self.move_history) > 0
		
	def has_redo(self):
		return len(self.redo_stack) > 0
		
class TestGUI (object):	
	def queue_animation(self, source_cards, dest_slot_index, dest_offset):
		print("%s, %d, %d" % (source_cards.__repr__(), dest_slot_index, dest_offset))

if __name__ == '__main__':
	game = Seahaven()
	game.gui = TestGUI()
	console.clear()
	while True:
		print(game)
		source = int(input("Move from: "))
		dest = int(input("Move to: "))
		count = int(input("How many? "))
		game.move(source, dest, count)

