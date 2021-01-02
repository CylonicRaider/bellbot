
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
        es: new EventSource(apiBaseURL + label + '/watch'),
        current: null
      };
      info.es.onmessage = function(event) {
        info.current = BellBotAPI._parseDeadline(event.data);
      };
      info.es.onerror = function(event) {
        if (deadlineTrackers[label] != info) return;
        delete deadlineTrackers[label];
      };
      deadlineTrackers[label] = info;
    },
    /* Delete the internal tracker of the given deadline. */
    _untrackDeadline: function(label) {
      if (! deadlineTrackers[label]) return;
      deadlineTrackers[label].es.close();
      delete deadlineTrackers[label];
    }
  };
  window.BellBotAPI = BellBotAPI;
}();
