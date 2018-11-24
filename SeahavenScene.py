from scene import *
import sound
import random
import math
import ui

from Seahaven import *

A = Action

class CardNode (SpriteNode):
	'''
	Node for a playing card.
	'''
	
	# used to construct the image name for specific cards
	image_suit_prefix = ["Clubs", "Diamonds", "Hearts", "Spades"]
	image_rank_suffix = [None, "A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
	
	def __init__(self, card):
		self.card = card
		super().__init__(self.image_name_for_card(card))
		
	def image_name_for_card(self, card):
		prefix = CardNode.image_suit_prefix[card.suit]
		suffix = CardNode.image_rank_suffix[card.rank]
		image_name = 'card:' + prefix + suffix
		return image_name
		
		
class PlacardNode (ShapeNode):
	'''
	Node for a placeholder.
	'''
	
	def __init__(self, size, suit=None):
			self.suit = suit
			border_path = ui.Path.rounded_rect(0, 0, size.width - 6.0, size.height - 6.0, 10)
			border_path.line_width = 4.0
			border_path.set_line_dash([10, 10])
			
			super().__init__(path=border_path, stroke_color='#000000', fill_color='clear')
			
			if suit is not None:
				suit_images = ['emj:Card_Clubs', 'emj:Card_Diamonds', 'emj:Card_Hearts', 'emj:Card_Spades']
				suit_node = SpriteNode(suit_images[suit])
				self.add_child(suit_node)


class ButtonNode (SpriteNode):
	
	PRESSED_COLOR = '#8b8b8b'
	NOT_PRESSED_COLOR = 'white'
		
	def __init__(self, image, identifier, action):
		super().__init__(image)
		self.scale = 0.3
		self.identifier = identifier
		self.action = action
		
	def set_pressed(self, pressed_state):
		if pressed_state:
			self.color = ButtonNode.PRESSED_COLOR
		else:
			self.color = ButtonNode.NOT_PRESSED_COLOR
			
	def set_enabled(self, enabled_state):
		if enabled_state:
			self.alpha = 1.0
		else:
			self.alpha = 0.3
			
	def perform_action(self):
		self.action()


class TableNode (SpriteNode):
	'''
	Node representing the game table. The geometry is fixed and independent of
	screen geometry. The entire table can be rotated and scaled in response to
	screen size changes.
	
	The actual geometry of the TableNode is based on the size of the built-in card
	images (prefixed by "card:").
	'''
	
	CHECK_FOR_DRAG = 0
	NOT_DRAGGING = 1
	DRAGGING =2
	
	def __init__(self):
		# Create a card node so we can get the width and height of a single
		# card. The size of the table will be based on that.
		card = CardNode(Card(Card.ace, Card.spades))
		self.card_size = card.size
		(self.card_width, self.card_height) = card.size
		
		# The width of the table needs to accomodate 10 cards and the gaps
		# between the cards and sides of the screen.
		h_gap_percent = 0.2
		self.h_gap = h_gap_percent*self.card_width
		table_width = self.card_width*10 + self.h_gap*11

		# The height of the table needs to accommodate 2 full cards heights
		# plus 3 + N gaps, where N is the maximum number of cards that we
		# can accommodate on a tower. The worst case scenario for tower
		# height is 5 + 12 = 17. So we need to accomodate 20 vertical gaps
		v_gap_percent = 0.3
		self.v_gap = v_gap_percent*self.card_height
		table_height = self.card_height*2 + self.v_gap*16
		
		super().__init__(color='#046e0d', size=(table_width, table_height))
		self.setup_placards()
		
		self.game = None 						# a Seahaven object
		self.card_nodes = {}				# Card -> CardNode
		
		self.current_touch = None
		
		# drag_cards is a node that is constructed during a drag. It's children are
		# the CardNode objects being dragged.
		self.drag_state = TableNode.CHECK_FOR_DRAG
		self.drag_cards = None
		self.move_source = None 		# (slot index, num cards)
		
		self.current_animation = None
		self.animation_node = None
		
		self.pressed_button = None
		self.selected_card = None
	
	def setup_placards(self):
		# Add suit placards
		suits_columns = [(Card.diamonds, 0), (Card.clubs, 1), (Card.hearts, 8), (Card.spades, 9)]
		for (suit, column) in suits_columns:				
			placard = PlacardNode(self.card_size, suit)
			placard.position = self.card_position_at(column, 0)
			self.add_child(placard)
			
		# Add free cell placards
		free_columns = [3, 4, 5, 6]
		for column in free_columns:
			placard = PlacardNode(self.card_size)
			placard.position = self.card_position_at(column, 0)
			self.add_child(placard)
			
		# Add tower placards
		for column in range(10):
			placard = PlacardNode(self.card_size)
			placard.position = self.card_position_at(column, 1)
			self.add_child(placard)
			
		# Add undo and redo buttons
		self.buttons = []
		buttons = [('iow:ios7_undo_256', 'undo', 2, self.undo), ('iow:ios7_redo_256', 'redo', 7, self.redo)]
		
		for button_info in buttons:
			(image, identifier, column, action) = button_info
			button = ButtonNode(image, identifier, action)
			button.position = self.card_position_at(column, 0)
			self.buttons.append(button)
			self.add_child(button)
	
	def undo(self):
		self.game.undo()
		self.process_next_animation()
		
	def redo(self):
		self.game.redo()
		self.process_next_animation()
		
	def card_position_at(self, column, row):
		'''
		Returns an (x, y) tuple representing the center of the card at the specified
		column and row.
		'''
		x = self.center_of_column(column)
		y = self.center_of_row(row)
		return self.rel_position(x, y)
		
	def card_position_at_slot(self, slot_index, dest_offset):
		 
		if slot_index < 10:
			position = self.card_position_at(slot_index, 1)
		elif slot_index < 14:
			position = self.card_position_at(3 + slot_index - 10, 0)
		else:
			map = [1, 0, 8, 9]
			position = self.card_position_at(map[slot_index - 14], 0)
			
		if dest_offset > 0:
			dy = dest_offset * self.v_gap
			(x, y) = position
			position = Point(x, y - dy)
			
		return position

	def card_frame_at(self, column, row, num_cards=1):
		'''
		Returns a Rect object representing the frame of the card at the specified
		column and row. An optional num_cards parameter specifies the number of
		cards in a tower based at column and row.
		'''
		(cx, cy) = self.card_position_at(column, row)
		x = cx - self.card_width/2
		h = self.card_height + num_cards*self.v_gap
		y = cy - (self.card_height/2 + num_cards*self.v_gap)
		w = self.card_width
		return Rect(x, y, w, h);
				
	def center_of_column(self, column):
		return self.h_gap*(column+1) + self.card_width*column + self.card_width/2
		
	def center_of_row(self, row):
		return self.v_gap*(row+1) + self.card_height*row + self.card_height/2
		
	def rel_position(self, x, y):
		rel_x = x - self.size.width/2
		rel_y = self.size.height/2 - y
		return (rel_x, rel_y)
		
	def set_game(self, game):
		for _, card_node in self.card_nodes.items():
			card_node.remove_from_parent()
		
		self.card_nodes = {}
		self.game = game
		self.animation_queue = []
		
		for i in range(10):
			tower = self.game.slots[i]
			d = 0
			for card in tower:
				card_node = CardNode(card)
				(x, y) = self.card_position_at(i, 1)
				y -= d * self.v_gap
				card_node.position = (x, y)
				self.card_nodes[card] = card_node
				self.add_child(card_node)
				d += 1
				
		for i in range(4):
			cell_slot = self.game.slot_for_cell(i)
			for card in cell_slot:
				card_node = CardNode(card)
				card_node.position = self.card_position_at(3+i, 0)
				self.card_nodes[card] = card_node
				self.add_child(card_node)
				
		suit_columns = [1, 0, 8, 9]
				
		for suit in Card.all_suits:
			suit_slot = self.game.slot_for_suit(suit)
			column = suit_columns[suit]
			for card in suit_slot:
				card_node = CardNode(card)
				card_node.position = self.card_position_at(column, 0)
				self.card_nodes[card] = card_node
				self.add_child(card_node)
				
		self.buttons[0].set_enabled(self.game.has_undo())
		self.buttons[1].set_enabled(self.game.has_redo())
				
	def find_slot_containing_point(self, location):
		'''
		Returns (slot_index, num_cards) tuple if location is in a cell or tower slot.
		Returns None if it is not. num_cards indicates the number of cards at or
		below location in a tower. If the tower/cell is empty, then num_cards is 0.
		'''
		for cell_index in range(4):
			num_cards = len(self.game.slot_for_cell(cell_index))
			if location in self.card_frame_at(3+cell_index, 0):
				return (cell_index+10, num_cards)
		
		for tower_index in range(10):
			num_cards_in_tower = len(self.game.slot_for_tower(tower_index))
			frame = self.card_frame_at(tower_index, 1, max(num_cards_in_tower, 1))
			if location in frame:
				if num_cards_in_tower < 2:
					num_cards = num_cards_in_tower
				else:
					dy = frame.y+frame.h - location.y
					card_index = min(int(dy//self.v_gap), num_cards_in_tower-1)
					num_cards = num_cards_in_tower - card_index
				return (tower_index, num_cards)
				
		return None
	
	def clear_selection(self):
		card = self.selected_card
		up_card = Card(card.rank+1, card.suit) if card.rank < Card.king else None
		down_card = Card(card.rank-1, card.suit) if card.rank > Card.ace else None

		self.card_nodes[card].color = 'white'
		if up_card:
			self.card_nodes[up_card].color = 'white'
		if down_card:
			self.card_nodes[down_card].color = 'white'
		
	def select_card(self, slot_index, num_cards):
		card = self.game.slots[slot_index][-num_cards]
		up_card = Card(card.rank+1, card.suit) if card.rank < Card.king else None
		down_card = Card(card.rank-1, card.suit) if card.rank > Card.ace else None
		
		selected_same_card = False
			
		if self.selected_card:
			self.clear_selection()
			if self.selected_card == card:
				self.selected_card = None
				return
			
		self.selected_card = card
		
		SELECTED_COLOR = '#8b8b8b'
		UP_COLOR = '#5ccdde'
		DOWN_COLOR = '#73de5c'
		
		self.card_nodes[card].color = SELECTED_COLOR
		
		if up_card:
			self.card_nodes[up_card].color = UP_COLOR
			
		if down_card:
			self.card_nodes[down_card].color = DOWN_COLOR
		
				
	def touch_began(self, touch):
		# don't process a new touch while a touch is in progress
		if self.current_touch:
			return
			
		self.current_touch = touch
		
		# convert to coordinate space of TableNode
		loc = self.point_from_scene(touch.location)
		
		# check for button press
		for button in self.buttons:
			if loc in button.frame:
				button.set_pressed(True)
				self.pressed_button = button
				return
				
	def touch_moved(self, touch):
		if self.current_touch and self.current_touch.touch_id != touch.touch_id:
			return
			
		loc = self.point_from_scene(touch.location)
		
		if self.pressed_button:
			if not loc in self.pressed_button.frame:
				self.pressed_button.set_pressed(False)
			else:
				self.pressed_button.set_pressed(True)
			return			
		
		if self.drag_state == TableNode.NOT_DRAGGING:
			return
			
		if self.drag_state == TableNode.CHECK_FOR_DRAG:
			start_loc = self.point_from_scene(self.current_touch.location)
			found_tuple = self.find_slot_containing_point(start_loc)
			if found_tuple is None: # bail if tap was outside of a cell or tower
				self.drag_state = TableNode.NOT_DRAGGING
				return
			else:
				(slot_index, num_cards) = found_tuple
				if num_cards == 0:	# bail if tap was in an empty slot
					self.drag_state = TableNode.NOT_DRAGGING
					return
					
				self.drag_state = TableNode.DRAGGING
							
				self.drag_cards = Node()
				self.drag_cards.z_position = 100.0
				self.drag_cards.alpha = 0.5
				self.drag_point = self.drag_cards.position - loc
				
				self.move_source = found_tuple
				
				# find the cards being dragged and add them to the drag_cards node
				(slot_index, num_cards) = found_tuple
				cards = self.game.slots[slot_index][-num_cards:]
				for card in cards:
					card_node = self.card_nodes[card]
					card_node.remove_from_parent()
					self.drag_cards.add_child(card_node)
				
				# Finally, add the drag_cards node to the table
				self.add_child(self.drag_cards)
		
		if self.drag_cards:
			self.drag_cards.position = self.drag_point + loc

	def touch_ended(self, touch):
		if self.current_touch and self.current_touch.touch_id != touch.touch_id:
			return

		loc = self.point_from_scene(touch.location)
		
		if self.pressed_button == None and self.drag_state == TableNode.CHECK_FOR_DRAG:
			found_tuple = self.find_slot_containing_point(loc)
			if found_tuple:
				(slot_index, num_cards) = found_tuple
				if num_cards > 0:
					self.select_card(slot_index, num_cards)
						
		self.current_touch = None
		self.drag_state = TableNode.CHECK_FOR_DRAG
		
		if self.pressed_button:
			if loc in self.pressed_button.frame:
				self.pressed_button.perform_action()
			self.pressed_button.set_pressed(False)
			self.pressed_button = None
			return

		# determine if the destination represents a valid move
		if self.drag_cards:
			is_valid_move = False
			dest_tuple = self.find_slot_containing_point(loc)
			if dest_tuple:
				(source_slot_index, num_cards) = self.move_source
				(dest_slot_index, _) = dest_tuple
				
				if source_slot_index == dest_slot_index:
					self.select_card(source_slot_index, num_cards)
				else:
					is_valid_move = self.game.move(source_slot_index, dest_slot_index, num_cards)
			
			delta_position = self.drag_cards.position
			for card_node in self.drag_cards.children:
				card_node.remove_from_parent()
				if is_valid_move:
					card_node.position += delta_position
				self.add_child(card_node)
			self.drag_cards = None
			
		self.process_next_animation()
			
	def queue_animation(self, source_cards, dest_slot_index, dest_offset):
		animation = (source_cards, dest_slot_index, dest_offset)
		self.animation_queue.append(animation)
		
	def process_next_animation(self):
		'''
		Perform next queued animation.
		'''
		DURATION = 0.2
		
		# Finish up current animation
		if self.current_animation:
			(source_cards, dest_slot_index, dest_offset) = self.current_animation
			(x, y) = self.card_position_at_slot(dest_slot_index, dest_offset)
			for card in source_cards:
				card_node = self.card_nodes[card]
				card_node.remove_from_parent()
				card_node.position = (x, y)
				self.add_child(card_node)
				y -= self.v_gap
			self.animation_node.remove_from_parent()
			self.current_animation = None
			self.animation_node = None
		
		if len(self.animation_queue) > 0:
			self.current_animation = self.animation_queue[0]
			del self.animation_queue[0]
			(source_cards, dest_slot_index, dest_offset) = self.current_animation
			self.animation_node = Node()
			for card in source_cards:
				card_node = self.card_nodes[card]
				card_node.remove_from_parent()
				self.animation_node.add_child(card_node)
			self.add_child(self.animation_node)
			first_card = self.card_nodes[source_cards[0]]
			dest_position = self.card_position_at_slot(dest_slot_index, dest_offset)
			delta_position = dest_position - first_card.position
			move_action = A.move_by(delta_position.x, delta_position.y, DURATION)
			call_action = A.call(self.process_next_animation)
			action_sequence = A.sequence(move_action, call_action)
			self.animation_node.run_action(action_sequence)
			
		self.buttons[0].set_enabled(self.game.has_undo())
		self.buttons[1].set_enabled(self.game.has_redo())		
		
class SeahavenScene (Scene):
	def setup(self):
		self.table = TableNode()
		self.table.set_game(Seahaven())
		self.table.game.gui = self.table
		
		self.add_child(self.table)
		self.did_change_size()
			
	def did_change_size(self):
		self.table.position = self.size/2
		x_scale = self.size.width / self.table.size.width
		y_scale = self.size.height / self.table.size.height		
		min_scale = min(x_scale, y_scale)
		self.table.x_scale = min_scale
		self.table.y_scale = min_scale
	
	def update(self):
		pass
	
	def touch_began(self, touch):
		if touch.location in self.table.frame:
			self.table.touch_began(touch)
	
	def touch_moved(self, touch):
		if touch.location in self.table.frame:
			self.table.touch_moved(touch)
			
	def touch_ended(self, touch):
		if touch.location in self.table.frame:
			self.table.touch_ended(touch)
			
			
if __name__ == '__main__':
	run(SeahavenScene(), show_fps=False)
	

