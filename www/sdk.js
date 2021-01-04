
'use strict';

void function() {
  /* The URL of this script (if available) for API endpoint auto-detection. */
  // This has to be fetched synchronously -- currentScript will be different
  // by the time init() is run.
  var thisURL = null;
  if (document.currentScript) thisURL = document.currentScript.src;
  /* The API's base URL. */
  var apiBaseURL = null;
  /* Mapping from deadline labels to tracker records. */
  var deadlineTrackers = {};
  /* The main export. */
  var BellBotAPI = {
    /* Initialize the API endpoint.
     * scriptID is the ID of the <script> element via which the SDK was
     * loaded; the URLs of the API endpoints are derived from it.
     * baseOverride overrides the script-element-based auto-detection
     * mechanism to provide an explicit base URL. */
    init: function(scriptID, baseOverride) {
      var effScriptURL;
      if (baseOverride) {
        apiBaseURL = baseOverride;
        return;
      } else if (scriptID) {
        var script = document.getElementById(scriptID);
        if (! script) throw new Error('Cannot locate SDK script');
        effScriptURL = script.src;
      } else if (thisURL) {
        effScriptURL = thisURL;
      } else {
        throw new Error('Cannot locate API endpoints');
      }
      apiBaseURL = new URL('.', effScriptURL).href;
    },
    /* Parse the given API-level representation of a deadline into its
     * JavaScript form. */
    _parseDeadline: function(value) {
      if (! /^\d+(\.\d+)?([eE][+-]?\d+)?$/.test(value)) return null;
      return parseFloat(value) * 1000;
    },
    /* Ensure the given deadline is tracked. */
    _trackDeadline: function(label) {
      if (deadlineTrackers[label]) return;
      var info = {
        label: label,
        es: new EventSource(apiBaseURL + label + '/watch'),
        value: null,
        listeners: []
      };
      info.es.onmessage = function(event) {
        if (deadlineTrackers[label] != info) {
          es.close();
          return;
        }
        info.value = BellBotAPI._parseDeadline(event.data);
        info.listeners.forEach(function(l) {
          l.call(info, info.value);
        });
      };
      info.es.onerror = function(event) {
        if (deadlineTrackers[label] != info) {
          es.close();
          return;
        }
        delete deadlineTrackers[label];
      };
      deadlineTrackers[label] = info;
    },
    /* Delete the internal tracker of the given deadline. */
    _untrackDeadline: function(label) {
      if (! deadlineTrackers[label]) return;
      deadlineTrackers[label].es.close();
      delete deadlineTrackers[label];
    },
    /* Listen for updates of the given deadline. */
    watchDeadline: function(label, callback) {
      BellBotAPI._trackDeadline(label);
      deadlineTrackers[label].push(callback);
    },
    /* Stop listening the given deadline's changes. */
    unwatchDeadline: function(label, callback) {
      if (! deadlineTrackers[label]) return;
      var listeners = deadlineTrackers[label].listeners;
      var index = listeners.indexOf(callback);
      if (index == -1) return;
      listeners.splice(index, 1);
      if (listeners.length) return;
      BellBotAPI._untrackDeadline(label);
    },
    /* Run the given callback at given deadline. */
    runAtDeadline: function(label, callback) {
      function onDeadline(deadline) {
        currentDeadline = deadline;
        maybeScheduleRun(deadline);
      }
      function maybeScheduleRun(deadline) {
        if (deadline != null && timeoutID == null) {
          timeoutID = setTimeout(function() {
            timeoutID = null;
            if (currentDeadline == deadline) {
              callback();
            } else {
              maybeScheduleRun(currentDeadline);
            }
          }, deadline - Date.now());
        } else if (deadline == null && timeoutID != null) {
          clearTimeout(timeoutID);
        }
      }
      function cancel() {
        if (timeoutID != null) clearTimeout(timeoutID);
        BellBotAPI.unwatchDeadline(label, onDeadline);
      }
      var timeoutID = null, currentDeadline = null;
      BellBotAPI.watchDeadline(label, onDeadline);
      callback._cancel_runAtDeadline = cancel;
    },
    /* Drop the given at-deadline callback. */
    dontRunAtDeadline: function(label, callback) {
      if (callback._cancel_runAtDeadline) {
        callback._cancel_runAtDeadline();
        delete callback._cancel_runAtDeadline;
      }
    }
  };
  window.BellBotAPI = BellBotAPI;
}();
