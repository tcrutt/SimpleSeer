Feature = require "models/feature"
module.exports = class blobs extends Feature
  ###
	initialize: (feature) ->
		@feature = feature
		super()
  ###
	icon: () => "/img/object.png" 
		
	represent: () =>
		"Blob at (" +    @feature.get("x") + "," + @feature.get("y") + 
			") with area " +
			@feature.get("featuredata").mArea + " and size (" +
			@feature.get("width") + "," +
			@feature.get("height") + ")."

	tableOk: => true

	tableHeader: () =>
		["X", "Y", "Width", "Height","Area","Mean Color"]

	tableData: () =>
		[@feature.get("x"),
		@feature.get("y"),
		@feature.get("width"),
		@feature.get("height"),
                @feature.get("featuredata").mArea,
                @feature.get("featuredata").mColor]
	  
	render: (pjs) =>
		pjs.stroke 255, 0, 255
		pjs.strokeWeight 3
		pjs.color c = pjs.color(255, 0, 255, 128)
		pjs.fill(c)
		contour = @feature.get('featuredata').mContourAppx
		last = contour[contour.length-1]
		for current in contour
			pjs.line( last[0],last[1],current[0],current[1] )
			last = current
		#plugin mount point to the class to what you defined
		# LHS - The name of the python class that is the feature
		# by the inspection
		# RHS - The name of this coffee script feature class.
#plugin this, Blob:BlobsFeature
