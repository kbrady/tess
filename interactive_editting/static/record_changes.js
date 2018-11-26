var changes = {};

// set box functions
var xMap = function(d){return d.left;};
var yMap = function(d){return d.top;};
var widthMap = function(d){return d.right - d.left;};
var heightMap = function(d){return d.bottom - d.top;};

// assign colors
var cat_color = d3.scale.category10();

// make a legend for the highlight categories
function makeLegend() {
	var counter = 0;

	// Label Legend
	svg.append("text")
  .attr("dx", 50 + 'px')
  .attr("dy", 85 + 'px')
  .style('fill-opacity', .9)
  .style('fill', 'black')
  .style('font-size', 18)
  .text('Highlight Legend:');

	colors.forEach(function(col) {
		// draw rect
		svg.append('rect')
		.attr("x", 50)
		.attr("y", 95 + counter * 20)
		.attr("width", 100)
		.attr("height", 15)
		.style("stroke", cat_color(col[0])) //D3 does the magic! 
		.style('fill-opacity', 0)
		.style('stroke-opacity', 1)
		.style('stroke-width', 1.5);

		// write label text
		svg.append("text")
	  .attr("dx", 55 + 'px')
	  .attr("dy", 95 + counter * 20 + 12 + 'px')
	  .style('fill-opacity', .9)
	  .style('fill', 'black')
	  .style('font-size', 14)
	  .text(col[0]);

	  // iterate counter
	  counter += 1;
	});
}

function change_all_to_white() {
	hidePopup();
	Array.prototype.slice.call(wordInfo).forEach(function(word) {
		var word_id = word.global_ids;
		var text = word.text;
		var color = 'white';

		changes[word_id] = [text, color];
		// get rid of the old bbox and replace with correct color word
		removeWord(word);
		updateWord(word_id, text, color);
	});
	changes_container.value = JSON.stringify(changes);
}

function change_all_to_mustard() {
	hidePopup();
	Array.prototype.slice.call(wordInfo).forEach(function(word) {
		var word_id = word.global_ids;
		var text = word.text;
		var color = 'mustard yellow';

		changes[word_id] = [text, color];
		// get rid of the old bbox and replace with correct color word
		removeWord(word);
		updateWord(word_id, text, color);
	});
	changes_container.value = JSON.stringify(changes);
}

function recordChanges() {
	var word_id = document.getElementById('global_ids_input').value;
	var text = document.getElementById('text_input').value;
	var color = '';
	var select = document.getElementById('highlight_select');
	Array.prototype.slice.call(select.childNodes).forEach(function(option) {
		if (option.tagName == 'OPTION') {
			if (option.selected) {
				color = option.value;
			}
		}
	});

	changes[word_id] = [text, color];
	changes_container.value = JSON.stringify(changes);
	updateWord(word_id, text, color);
	hidePopup();
}

function cancelChanges() {
	var word_id = document.getElementById('global_ids_input').value;
	if (word_id.length > 0) {
		if (word_id in changes) {
			updateWord(word_id, changes[word_id][0], changes[word_id][1]);
		} else {
			var my_word = wordInfo.filter(function (d) { return d.global_ids == word_id; })[0];
			addWord(my_word);
		}
	}
	hidePopup();
}

function addWord(d) {
	// make sure the word isn't allready around
	if (d3.select('#' + to_id(d.global_ids) + '_box')[0][0] != null) { return; }
	
	// Draw rectangle
	svg.append('rect')
		.attr("class", "bbox")
		.attr('id', to_id(d.global_ids) + '_box')
		.attr("x", xMap(d))
		.attr("y", yMap(d))
		.attr("width", widthMap(d))
		.attr("height", heightMap(d))
		.style("stroke", cat_color(d.highlight)) //D3 does the magic! 
		.style('fill-opacity', 0)
		.style('stroke-opacity', 1)
		.style('stroke-width', 1.5)
		.attr('data', d.global_ids)
		.on('click', function(e) {makePopup(d);});

	// Write text
	svg.append("text")
	  .attr('class', 'text_label')
	  .attr('id', to_id(d.global_ids) + '_text')
	  .attr("dx", xMap(d) + 'px')
	  .attr("dy", yMap(d) + 'px')
	  .style('fill-opacity', .9)
	  .style('fill', 'black')
	  .style('font-size', 11)
	  .text(d.text);
}

function to_id(numeric_id) {
	output = '';
	[...numeric_id].forEach(function(c) {
		diff = c - '0';
		if (diff >= 0 && diff < 10) {
			output += String.fromCharCode(97 + diff);
		}
	})
	return output;
}

function removeWord(d) {
	// Delete rectangle
	var box = d3.select('#' + to_id(d.global_ids) + '_box')[0][0];
	box.remove();

	// Delete text
	var text = d3.select('#' + to_id(d.global_ids) + '_text')[0][0];
	text.remove();
}

function updateWord(word_id, text, color) {
	var my_word = wordInfo.filter(function (d) { return d.global_ids == word_id; })[0];
	var new_word = {};
	Object.keys(my_word).forEach(function(k) {
		if (k == 'text') {
			new_word[k] = text;
			return;
		}
		if (k == 'highlight') {
			new_word[k] = color;
			return;
		}
		new_word[k] = my_word[k];
	});
	// already removed for editting
	// removeWord(my_word);
	addWord(new_word);
}

function makePopup(d) {
	cancelChanges();

	d3.select("#change_value_form")
	.style('display', 'block')
	.style('visibility', 'visible');

	// set the text to the value for this word
	document.getElementById("text_input").value = d.text;

	// set the word being updated
	d3.select("#global_ids_input").attr('value', d.global_ids);

	// update the highlight color dropdown
	var select = document.getElementById('highlight_select');
	Array.prototype.slice.call(select.childNodes).forEach(function(option) {
		if (option.tagName == 'OPTION') {
			if (option.value == d.highlight) {
				option.selected = true;
			} else {
				option.selected = false;
			}
		}
	});

	// get rid of the old bbox (too small)
	removeWord(d);

	// Draw a rectangle to highlight the word being editted
	svg.append('rect')
		.attr("class", "box_editted")
		.style("stroke", 'red')
		.style('fill-opacity', 0)
		.style('stroke-opacity', 1)
		.style('stroke-width', 3)
		.attr("x", xMap(d) - 3)
		.attr("y", yMap(d) - 3)
		.attr("width", widthMap(d) + 6)
		.attr("height", heightMap(d) + 6);
}

function hidePopup() {
	d3.select("#change_value_form")
	.style('display', 'none')
	.style('visibility', 'hidden');

	svg.selectAll('rect.box_editted').remove();
}
