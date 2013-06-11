Modal = require("views/core/modal")

describe "Modal", ->
  m = undefined
  el = undefined
  options = undefined

  beforeEach ->
    m = new Modal()
    el = m.$el
    options =
      title: "Test Title"
      message: "Test Message"
      success: jasmine.createSpy("dummySuccess")
      error: jasmine.createSpy("dummyError")

  it "should extend View", ->
    expect(m instanceof View).toBe true

  describe "#show", ->
    m.show options
    console.log m.el.innerHTML
    it "should display a title", ->
      expect(el.find(".title").html()).toEqual options.title

    it "should display a message", ->
      expect(el.find(".message").html()).toEqual options.message


  describe "#onSuccess", ->
    m.onSuccess()
    it "should run the success callbacks", ->
      expect(options.success).toHaveBeenCalled()

    it "should not run the error callbacks", ->
      expect(options.error).not.toHaveBeenCalled()


  describe "#onCancel", ->
    m.onCancel()
    it "should not run the success callbacks", ->
      expect(options.success).not.toHaveBeenCalled()

    it "should run the error callbacks", ->
      expect(options.error).toHaveBeenCalled()
