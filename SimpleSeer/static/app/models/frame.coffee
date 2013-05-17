Model = require "./model"
application = require "application"

module.exports = class Frame extends Model
  urlRoot: "/api/frame"

  parse: (response) =>
    ###
    if response.results and response.results.length
      for r in response.features
        try
          plugin = require "plugins/feature/"+r.inspection_name.toLowerCase()
          #console.log "plugins/feature/"+r.inspection_name.toLowerCase(), plugin
          if !response.features[r.inspection_name]?
            response.features[r.inspection_name] = new plugin()
          response.features[r.inspection_name].addTrait(r)
        catch e
          if application.debug
            console.info "Error loading javascript plugin feature:"
            console.error e
    ###
    features = response.features
    response.features = {}
    if features and features.length
      for f in features
        name = f.featuretype.toLowerCase()
        try
          plugin = require "plugins/feature/"+name
          if !response.features[name]?
            response.features[name] = new plugin(f)
        catch e
          if application.debug
            console.info "Error loading javascript plugin feature:"
            console.error e

    if not response.thumbnail_file? or not response.thumbnail_file
      response.thumbnail_file = "/grid/thumbnail_file/" + response.id
    return response
    
  save:(attributes, options)=>
    if @attributes.features?
      delete @attributes.features
    if @attributes.results?
      delete @attributes.results      
    super(attributes, options)
