'use strict';

/*
 * Purpose:
 *   The view the user sees when no region has been seleted
 * Dependencies:
 *   jQuey, audio-annotator.css
 */
function StageOneView() {
    this.dom = null;
}

StageOneView.prototype = {
    // Create dom
    create: function () {
        var my = this;
        var container = $('<div>');
        var time = Util.createSegmentTime();
        time.hide();
        this.dom = container.append([time]);
    },

    // Update start and end times. Enable the 'CLICK TO START A NEW ANNOTATION' if the audio is playing
    update: function (start, end, enableCreate) {
        $('.start', this.dom).val(Util.secondsToString(start));
        $('.end', this.dom).val(Util.secondsToString(end));
    },
};

/*
 * Purpose:
 *   The view the user sees when they are creating an annotation in online mode,
 *   (the region grows as the audio plays). This view is not used if the current version
 *   of the interface
 * Dependencies:
 *   jQuey, audio-annotator.css
 */
function StageTwoView() {
    this.dom = null;
}

StageTwoView.prototype = {
    // Create dom
    create: function () {
        var my = this;
        var container = $('<div>');
        var button = $('<button>', {
            class: 'btn btn_stop',
            text: 'CLICK TO END ANNOTATION',
        });
        button.click(function () {
            $(my).trigger('stop-annotation');
        });

        var time = Util.createSegmentTime();

        this.dom = container.append([button, time]);
    },

    // Update start, end and duration times
    update: function (region) {
        $('.start', this.dom).val(Util.secondsToString(region.start));
        $('.end', this.dom).val(Util.secondsToString(region.end));
        $('.duration', this.dom).val(Util.secondsToString(region.end - region.start));
    },
};

/*
 * Purpose:
 *   The view the user sees when they have a region selected
 * Dependencies:
 *   jQuey, audio-annotator.css
 */
function StageThreeView() {
    this.dom = null;
    this.editOptionsDom = null;
    // Note that this assumes there are never more than 3 proximity labels
    this.colors = ['#ffa69e', '#faf3dd', '#b8f2e6', '#aed9e0', '#5e6472'];
    this.colors.forEach(function (color, index) {
        $('<style>.annotation_tag:hover, .radio' + index + '.selected{background-color: ' + color + '}</style>').appendTo('head');
    });
}

StageThreeView.prototype = {
    // Create dom
    create: function () {
        var my = this;
        var container = $('<div>');

        var message = $('<div>', {
            class: 'stage_3_message'
        });

        var time = Util.createSegmentTime();

        time.hide();

        var button = $('.audio_visual');
        button.click(function () {
            time.show();
        });

        var tagContainer = $('<div>', {
            class: 'mytable',
        });

        this.dom = container.append([message, time, tagContainer]);
    },

    // Replace the proximity and annotation elements with the new elements that contain the
    // tags in the proximityTags and annotationTags lists
    updateTagContents: function (annotationTags, pass_id) {
        $('.mytable').html('');

        // var proximity = this.createProximityTags(proximityTags);
        var annotation = this.createAnnotationTags(annotationTags, pass_id);
        // $('.tag_container', this.dom).append([annotation, proximity]);
        $('.mytable', this.dom).append([annotation]);
    },

    createSpeechAnnotation: function () {
        var my = this;
        var mytable = $('.mytable');


        var label_span = $('<span>', {
            class: 'annotation_tags',
            id: 'annotation00',
        });

        var button_span = $('<input>', {
            type: 'radio',
            name: 'radio',
            class: 'radio annotation_tag',
            id: 'radio00',
            'disabled': 'disabled'
        });

        var label_name = $('<label>', {
            id: 'speech00',
            for: 'radio00',
            text: 'Speech',
        });
        var div_container = $('<div>', { // container
            class: 'labels00',
        });
        div_container.css({
            "width": "85%",
            "margin": "auto",
        });

        var label_checkbox = $('<label>', {
            class: 'label_checkbox',
            for: 'checkbox00',
            // text: "Highlight " + tagName,
        });

        var button_name = label_span.append(button_span)
        mytable.append(label_span.append(button_name.append(label_name)))
        mytable.append(label_checkbox)
        mytable.append(div_container)
    },
    // Create annotation tag elements
    createAnnotationTags: function (annotationTags, pass_id) {
        var my = this;
        var mytable = $('.mytable');

        if (pass_id === '3') {
            this.createSpeechAnnotation()
        }
        annotationTags.forEach(function (tagName, index) {
            var label_span = $('<span>', {
                class: 'annotation_tags',
                id: 'annotation' + index,
            });

            var button_span = $('<input>', {
                type: 'radio',
                name: 'radio',
                class: 'radio annotation_tag',
                id: 'radio' + index,
            });

            var label_name = $('<label>', {
                for: 'radio' + index,
                text: tagName,
            });
            var div_container = $('<div>', { // container
                class: 'labels' + index,
            });
            div_container.css({
                "width": "85%",
                "margin": "auto",
            });

            var label_checkbox = $('<label>', {
                class: 'label_checkbox',
                for: 'checkbox' + index,
            });

            var check_box = $('<input>', {
                class: 'button_highlightt filled-in ',
                id: 'checkbox' + index,
                name: 'checkbox' + index,
                type: 'checkbox',
                "data-position": "right",
                "data-tooltip": "Highlight " + tagName,
                'checked': 'checked'
            })
            console.log(pass_id)
            label_checkbox.append(check_box)
            var button_name = label_span.append(button_span)
            mytable.append(label_span.append(button_name.append(label_name)))
            mytable.append(label_checkbox)
            mytable.append(div_container)
        });

        $("#radio0").prop("checked", true);
    },

    // Update stage 3 dom with the current regions data
    update: function (region) {
        this.updateTime(region);
        this.updateSelectedTags(region);
    },

    // Update the start, end and duration elements to match the start, end and duration
    // of the selected region
    updateTime: function (region) {
        $('.start', this.dom).val(Util.secondsToString(region.start));
        $('.end', this.dom).val(Util.secondsToString(region.end));
        $('.duration', this.dom).val(Util.secondsToString(region.end - region.start));
    },

    // Update the elements of the proximity and annotation tags to highlight
    // which tags match the selected region's current annotation and proximity
    updateSelectedTags: function (region) {
        $('.annotation_tag', this.dom).removeClass('selected');
        $('.custom_tag input', this.dom).val('');
        $('.annotation_tag', this.dom).removeClass('disabled');

        if (region.annotation) {
            var selectedTags = $('.annotation_tag', this.dom).filter(function () {
                return this.innerHTML === region.annotation;
            });
            if (selectedTags.length > 0) {
                selectedTags.addClass('selected');
            } else {
                $('.custom_tag input', this.dom).val(region.annotation);
            }
        }

    }
};

/*
 * Purpose:
 *   Control the workflow of annotating regions.
 * Dependencies:
 *   jQuey, audio-annotator.css, Wavesurfer (lib/wavesurfer.js), Message (src/message.js)
 */
function AnnotationStages(wavesurfer) {
    this.currentStage = 0;
    this.currentRegion = null;
    this.usingProximity = false;
    this.stageOneView = new StageOneView();
    this.stageTwoView = new StageTwoView();
    this.stageThreeView = new StageThreeView();
    this.wavesurfer = wavesurfer;

    this.undo_stack = []
    this.redo_stack = []

    this.flag_performing_undo_or_redo = false
    this.deleteRegions = false // for making sure that when going to a new task, deleting previous labels do not count as a delete log
    this.createRegions = false // for making sure that when going to a new task, creating previous labels do not count as a create log
    this.deletedAnnotations = [];
    this.annotationSolutions = [];
    this.city = '';
    this.previousF1Score = 0;
    this.events = [];

    // These are not reset, since they should only be shown for the first clip
    this.shownTagHint = false;
    this.shownSelectHint = false;

    this.blockDeselect = false;
}

AnnotationStages.prototype = {
    // Create the different stages dom and append event handlers
    create: function () {
        // Add events
        this.addStageOneEvents();
        this.addStageTwoEvents();
        this.addStageThreeEvents();
        this.addWaveSurferEvents();


        // Create dom
        this.stageOneView.create();
        this.stageTwoView.create();
        this.stageThreeView.create();

    },

    // Extract the important information from a region object
    getAnnotationData: function (region) {
        var regionData = {
            'id': region.id,
            'start': region.start,
            'end': region.end,
            'annotation': region.annotation
        };
        return regionData;
    },

    loadAnnotations: function () {


        for (var region_id in this.wavesurfer.regions.list) {
            var region = this.wavesurfer.regions.list[region_id];

        }
    },

    // Return an array of all the annotations the user has made for this clip
    getAnnotations: function (pass_id) {
        var annotationData = [];
        if (this.wavesurfer.regions) {
            for (var region_id in this.wavesurfer.regions.list) {

                var region = this.wavesurfer.regions.list[region_id];
                var annotation_data = this.getAnnotationData(region)
                if (pass_id === '3') {
                    if (annotation_data.annotation !== 'Speech') {
                        annotationData.push(annotation_data);
                    }
                } else {
                    annotationData.push(annotation_data);
                }


            }
        }
        return annotationData;
    },

    // Return an array of all the annotations the user has created and then deleted for this clip
    getDeletedAnnotations: function () {
        var annotationData = [];
        var length = this.deletedAnnotations.length;
        for (var i = 0; i < length; ++i) {
            annotationData.push(this.getAnnotationData(this.deletedAnnotations[i]));
        }
        return annotationData;
    },

  
    // Switch the currently selected region
    swapRegion: function (newStage, region) {
        if (this.currentRegion) {
            this.currentRegion.update({drag: false, resize: false});
            $(this.currentRegion.element).removeClass('current_region');
            $(this.currentRegion.annotationLabel.element).removeClass('current_label');

            // Remove the highlated label and disable.
            $('.annotation_tag', this.dom).removeClass('selected');
            $('.annotation_tag', this.dom).addClass('disabled');

        }

        // If the user is switch to stage 3, enable drag and resize editing for the new current region. 
        // Also highlight the label and region border
        if (region) {
            if (newStage === 2) {
                region.update({drag: false, resize: false});
            } else if (newStage === 3) {
                region.update({drag: true, resize: true});
                $(region.element).addClass('current_region');
                $(region.annotationLabel.element).addClass('current_label');
            }
        }
        this.currentRegion = region;
    },

    clickDeselectCurrentRegion: function () {
        if (this.blockDeselect) {
            // A new region was created, block the subsequent click to not deselect
            this.blockDeselect = false;
        } else {
            if (this.currentRegion != null) {
                // Disable drag and resize editing for the old current region. 
                // Also remove the highlight of the label and region border
                this.currentRegion.update({drag: false, resize: false});
                $(this.currentRegion.element).removeClass('current_region');
                $(this.currentRegion.annotationLabel.element).removeClass('current_label');

                // Remove the highlated label and disable.
                $('.annotation_tag', this.dom).removeClass('selected');
                $('.annotation_tag', this.dom).addClass('disabled');
            }
        }
    },

    // Switch stages and the current region
    updateStage: function (newStage, region) {
        // Swap regions 
        this.swapRegion(newStage, region);

        // Update the dom of which ever stage the user is switching to
        var newContent = null;
        newContent = this.stageThreeView.dom;

        if (newContent) {
            // Update current stage
            this.currentStage = newStage;

            // Detach the previous stage dom and append the updated stage dom to the stage container
            var container = $('.creation_stage_container');
            container.hide(10, function () {
                container.children().detach();
                container.append(newContent).show();
            });
        }
        // Alert the user of a hint
        this.hint();
    },

    // Alert users of hints about how to use the interface
    hint: function () {
        // if (this.wavesurfer.regions && Object.keys(this.wavesurfer.regions.list).length === 1) {
        //     if (this.currentStage === 1 && !this.shownSelectHint) {
        //         // If the user deselects a region for the first time and have not seen this hint,
        //         // alert them on how to select and deselect a region
        //         Message.notifyHint('Double click on a segment to select or deselect it.');
        //         this.shownSelectHint = true;
        //     }
        //     if (this.currentStage === 3 && !this.shownTagHint) {
        //         // When the user makes a region for the first time, if they have not seen this hint,
        //         // alert them on how to annotate a region
        //         Message.notifyHint('You can resize, move or delete a region with the mouse.');
        //         this.shownTagHint = true;
        //     }
        // }
    },

    // Reset the field values (except for hint related fields)
    clear: function () {
        this.currentStage = 0;
        this.currentRegion = null;
        this.annotationSolutions = [];
        // this.wavesurfer.unAll();
        this.deleteRegions = true
        this.wavesurfer.clearRegions();
        this.deleteRegions = false
        this.events = [];
        this.deletedAnnotations = [];
        this.redo_stack = []
        this.undo_stack = []
        this.flag_performing_undo_or_redo = false
        $("#redobtn").attr("disabled", "disabled");
        $("#undobtn").attr("disabled", "disabled");
    },

    // Reset field values and update the proximity tags, annotation tages and annotation solutions
    reset: function (annotationTags, pass_id) {

        this.clear();
        // Update all Tags' Contents
        this.updateContentsTags(annotationTags, pass_id);
        // this.wavesurfer.on('region-removed', this.deleteAnnotation.bind(this));
    },

    addEventsHighlighter: function (annotationTags) {
        this.stageThreeView.updateSelectedTags(annotationTags)
    },

    // Update stage 3 dom with new proximity tags and annotation tags
    updateContentsTags: function (annotationTags, pass_id) {
        this.stageThreeView.updateTagContents(
            annotationTags, pass_id
        );
    },

    // Event Handler: For online creation mode, in stage 2 the current region's size grows as the audio plays
    updateEndOfRegion: function () {
        var current = this.wavesurfer.getCurrentTime();
        if (this.currentStage === 2 && current > this.currentRegion.end) {
            this.currentRegion.update({
                end: current
            });
            this.stageTwoView.update(this.currentRegion);
        }
    },

    // Event Handler: when the user finishes drawing the region, track the action and 
    // select the new region and switch to stage 3 so the user can tag the region
    createRegionSwitchToStageThree: function (region) {

        if (region !== this.currentRegion) {
            this.blockDeselect = true;
            console.log(region)
            this.trackEvent('offline-create', region.id, region.annotation, region.start.toFixed(2), region.end.toFixed(2));
            this.updateStage(3, region);
            this.redo_stack = []
            this.undo_stack.push({
                'event': 'create',
                'id': region.id,
                'start': region.start,
                'end': region.end,
                'annotation': region.annotation
            })
            $("#redobtn").attr("disabled", "disabled");
            document.querySelector('#undobtn').removeAttribute('disabled');
            // console.log(this.undo_stack)
        }
    },

    // Event handler: Called when a region is selected by dbl clicking the region or its label
    switchToStageThree: function (region) {
        if ($(region.element.classList.contains('not_clickable'))[0] === true) {
        } else {
            if (region !== this.currentRegion) {
                this.trackEvent('select-for-edit', region.id);
                this.updateStage(3, region);

            } else {
                this.trackEvent('deselect', region.id);
                this.updateStage(1);
            }
        }


    },

    // Event Handler: Update stage 3 dom with the the current region's data when the region data
    // has been changed
    updateStartEndStageThree: function () {
        if (this.currentStage === 3) {
            this.stageThreeView.updateTime(this.currentRegion);
        }
    },

    // Event handler: called when the a region is draged or resized, adds action to event list
    trackMovement: function (region, event, type) {
        if (this.currentStage === 3) {
            // this.giveFeedback();
            this.trackEvent('region-moved-' + type, this.currentRegion.id, region.annotation, this.currentRegion.start.toFixed(2), this.currentRegion.end.toFixed(2));
            this.redo_stack = []
            this.undo_stack.push({
                'event': type,
                'id': region.id,
                'start': region.start,
                'end': region.end,
                'annotation': region.annotation
            })
            $("#redobtn").attr("disabled", "disabled");
            document.querySelector('#undobtn').removeAttribute('disabled');


        }
    },

    // Event handler: called when there is audio progress. Updates the online creation
    // button if the audio is playing
    updateStageOne: function () {
        if (this.currentStage === 1) {
            this.stageOneView.update(
                null,
                null,
                this.wavesurfer.isPlaying()
            );
        }
    },

    // Event handler: Update stage one view region's start, end and duration as the user draws the region
    updateStageOneWhileCreating: function (region) {
        if (this.currentStage === 1) {
            this.stageOneView.update(
                region.start,
                region.end,
                this.wavesurfer.isPlaying()
            );
        }
    },

    createAnnotation: function (start, end) {
        this.createRegions = true
        var region = this.wavesurfer.addRegion({
            start: start,
            end: end,
        });


        // region.update({start: start, end: end})
        // console.log("after update",(region))
        this.updateStage(2, region);
        this.createRegions = false
    },

    createspeechAnnotation: function (start, end) {
        var region = this.wavesurfer.addRegion({
            start: start,
            end: end,
        });
        $(region.element).addClass('not_clickable');
        $(region.annotationLabel.element).addClass('not_clickable');
        region.update({drag: false, resize: false});
        region.annotationLabel.deleteRegion.remove() // remove delete icon from label
    },

    createAnnotationWithId: function (id, start, end) {
        var region = this.wavesurfer.addRegion({
            id: id,
            start: start,
            end: end,
        });
        this.updateStage(2, region);
    },
    // Event Handler: For online creation mode, called when the user clicks start creating annotation
    // Creates a region and switches to stage 2 where the region grows as the audio plays
    startAnnotation: function () {
        var region = this.wavesurfer.addRegion({
            start: this.wavesurfer.getCurrentTime(),
            end: this.wavesurfer.getCurrentTime() + 2,
        });
        this.updateStage(2, region);
    },

    // Event Handler: For online creation mode, called when the user clicks stop creating annotation.
    // Switches to stage 3 where the user can annotate the newly created region
    stopAnnotation: function () {
        if (this.wavesurfer.isPlaying()) {
            this.wavesurfer.pause();
        }
        this.trackEvent('online-create', this.currentRegion.id, this.annotation, this.currentRegion.start.toFixed(2), this.currentRegion.end.toFixed(2));
        this.updateStage(3, this.currentRegion);
    },

    // Event Handler: called when region is deleted
    deleteAnnotation: function (region) {
        // Add the action to the event list
        if (!this.flag_performing_undo_or_redo & !this.deleteRegions) {
            this.trackEvent('delete', region.id);
            // Add the region to the deleted list
            this.redo_stack = []
            this.undo_stack.push({
                'event': 'delete',
                'id': region.id,
                'start': region.start,
                'end': region.end,
                'annotation': region.annotation
            })
            $("#redobtn").attr("disabled", "disabled");
            document.querySelector('#undobtn').removeAttribute('disabled');
            this.deletedAnnotations.push(region);
        }
        // this.deletedAnnotations.push(region);
        // If that region was currently selected, switch back to stage 1
        if (region === this.currentRegion) {
            this.updateStage(1);
        }
    },

    myupdateRegion: function (data) {
        this.currentRegion.update(data);
    },
    // Event handler: called when a region's tags are added or changed
    updateRegion: function (data) {

        var annotationEventType = null;
        // var proximityEventType = null;

        // Determine if the tags where added for the first time or just changed
        if (data.annotation && data.annotation !== this.currentRegion.annotation) {
            annotationEventType = this.currentRegion.annotation ? 'change' : 'add';
        }

        // Update the current region with the tag data
        this.currentRegion.update(data);
        // Give feedback if these tags improve the user's f1 score

        // Track tag change / add events
        if (annotationEventType) {
            this.trackEvent(
                annotationEventType + '-annotation-label',
                this.currentRegion.id,
                this.currentRegion.annotation
            );
        }

        // If the region has all its required tags, deselect the region and go back to stage 1
        // if (this.currentRegion.annotation && (!this.usingProximity || this.currentRegion.proximity)) {
        this.updateStage(1);
        // }
    },

    // Event Handler: triggered when region is first started to be created, adds action to event list
    trackBeginingOfRegionCreation: function (region) {
        if (!this.createRegions) {
            this.trackEvent('start-to-create', region.id);
            $(region.element).addClass('current_region');
        }
    },

    // Event Handler: triggered when region is first started to be created
    // switch back to stage one while the user drags to finish creating the region
    switchToStageOneOnCreate: function () {
        if (this.currentStage !== 1) {
            this.updateStage(1);
        }
    },

    // Adds event tracking object to events list
    trackEvent: function (eventString, regionId, regionLabel, regionStart, regionEnd) {
        var extra_info = {}
        var eventData = {
            event: eventString,
            time: new Date().getTime(),
            region_id: regionId
        };
        extra_info.region_id = regionId
        // If the region's current label is passed in, append it to the event data
        if (regionLabel) {
            eventData.region_label = regionLabel;
            extra_info.region_label = regionLabel
        }

        if (regionStart) {
            eventData.region_start = regionStart;
            extra_info.region_start = regionStart;
        }

        if (regionEnd) {
            eventData.region_end = regionEnd;
            extra_info.region_end = regionEnd;
        }
        var request = $.ajax({
            url: "/saveTelemetry",
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify({
                action: eventString,
                annotation_type: 'fg',
                task_id: task_id,
                batch_number: batch_number,
                extra_info: extra_info
            }),
        })
        this.events.push(eventData);
        // console.log(eventData)
    },

    getUndoStack: function () {
        return this.undo_stack.slice()
    },

    getRedoStack: function () {
        return this.redo_stack.slice()
    },

    updateUndoStack: function (undo_stack) {
        this.undo_stack = undo_stack
    },

    updateRedoStack: function (redo_stack) {
        this.redo_stack = redo_stack
        // console.log(this.redo_stack)
    },

    // Return a list of actions the user took while annotating this clip
    getEvents: function () {
        // Return shallow copy
        return this.events.slice();
    },

    // Event handler: triggered when a region is played, adds this action to the event list
    trackPlayRegion: function (region) {
        this.trackEvent('play-region', region.id);
    },

    // Attach event handlers for wavesurfer events
    addWaveSurferEvents: function () {
        this.wavesurfer.enableDragSelection();
        this.wavesurfer.on('audioprocess', this.updateEndOfRegion.bind(this));
        this.wavesurfer.on('audioprocess', this.updateStageOne.bind(this));
        this.wavesurfer.on('pause', this.updateEndOfRegion.bind(this));
        this.wavesurfer.on('region-play', this.trackPlayRegion.bind(this));
        this.wavesurfer.on('region-dblclick', this.switchToStageThree.bind(this));
        this.wavesurfer.on('label-click', this.switchToStageThree.bind(this));
        this.wavesurfer.on('region-update-end', this.trackMovement.bind(this));
        this.wavesurfer.on('region-update-end', this.createRegionSwitchToStageThree.bind(this));
        this.wavesurfer.on('region-update-end', this.updateStartEndStageThree.bind(this));
        this.wavesurfer.on('region-updated', this.updateStartEndStageThree.bind(this));
        this.wavesurfer.on('region-updated', this.updateStageOneWhileCreating.bind(this));
        this.wavesurfer.on('region-updated', this.stageThreeView.updateSelectedTags.bind(this));
        this.wavesurfer.on('region-created', this.trackBeginingOfRegionCreation.bind(this));
        this.wavesurfer.on('region-created', this.switchToStageOneOnCreate.bind(this));
        this.wavesurfer.on('region-removed', this.deleteAnnotation.bind(this));
    },

    // Attach event handlers for stage one events
    addStageOneEvents: function () {
        $(this.stageOneView).on('start-annotation', this.startAnnotation.bind(this));
    },

    // Attach event handlers for stage two events
    addStageTwoEvents: function () {
        $(this.stageTwoView).on('stop-annotation', this.stopAnnotation.bind(this));
    },

    // Attach event handlers for stage three events
    addStageThreeEvents: function () {
        $(this.stageThreeView).on('change-tag', this.updateRegion.bind(this));
    },
};
